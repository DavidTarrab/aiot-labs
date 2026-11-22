"""Offline checkpoint 3 checks; no Gemini calls or ESP32 hardware required."""
import json
import os
from datetime import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import lab5_dt2811_ms7635_rnb2135_check3 as app


class CommandValidationTests(unittest.TestCase):
    def test_supported_commands(self):
        for name, count in app.COMMAND_ARGUMENTS.items():
            args = ['A short answer'] if name == 'display_text' else [16, 30, 0] if count else []
            command = {'name': name, 'args': args}
            with self.subTest(name=name):
                self.assertEqual(app.parse_command(json.dumps(command)), command)

    def test_invalid_commands(self):
        invalid = [
            {}, [], {'name': 'eval', 'args': []},
            {'name': 'screen_on', 'args': [1]},
            {'name': 'screen_on', 'args': [], 'extra': 1},
            {'name': 'set_alarm', 'args': [24, 0, 0]},
            {'name': 'set_alarm', 'args': [1, 60, 0]},
            {'name': 'set_alarm', 'args': [1, 0, -1]},
            {'name': 'set_alarm', 'args': [True, 0, 0]},
            {'name': 'set_alarm', 'args': [1.0, 0, 0]},
            {'name': 'set_alarm', 'args': ['16', 30, 0]},
            {'name': 'display_text', 'args': ['']},
            {'name': 'display_text', 'args': ['a' * 49]},
            {'name': 'display_text', 'args': ['Unicode: é']},
            {'name': 'display_text', 'args': ['newline\n']},
        ]
        for command in invalid:
            with self.subTest(command=command), self.assertRaises(ValueError):
                app.validate_command(command)
        for text in ['', 'garbage', '```json\n{}\n```', '{} {}']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                app.parse_command(text)

    def test_48_character_boundary(self):
        app.validate_command({'name': 'display_text', 'args': ['a' * 48]})

    def test_prompt_rollover_and_current_date(self):
        now = datetime(2026, 10, 14, 23, 58, 45, tzinfo=ZoneInfo('America/New_York'))
        prompt = app.build_prompt('Set an alarm in five minutes', now)
        self.assertIn('2026-10-14T23:58:45-04:00', prompt)
        self.assertIn('"args": [0, 3, 45]', prompt)
        self.assertIn('48 printable ASCII', app.SYSTEM_PROMPT)
        self.assertIn('4:30 PM -> [16,30,0]', app.SYSTEM_PROMPT)



class InterpretationTests(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_request_and_structured_response(self):
        from google.genai import types
        remote = MagicMock()
        remote.models.generate_content = AsyncMock(return_value=types.GenerateContentResponse(
            candidates=[types.Candidate(content=types.Content(parts=[types.Part(
                text='{"name":"set_alarm","args":[16,30,0]}'
            )]))]
        ))
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=remote)
        context.__aexit__ = AsyncMock(return_value=False)
        sdk_client = MagicMock(aio=context)
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'fake-key', 'GEMINI_MODEL': 'gemini-3.5-flash-lite'}), \
             patch('google.genai.Client', return_value=sdk_client) as factory:
            result = await app.get_llm_response('Set an alarm for 4:30 PM')
            self.assertEqual(json.loads(result), {'name': 'set_alarm', 'args': [16, 30, 0]})
            config = remote.models.generate_content.call_args.kwargs['config']
            self.assertEqual(config.response_mime_type, 'application/json')
            self.assertEqual(config.response_json_schema, app.COMMAND_SCHEMA)
            self.assertEqual(config.system_instruction, app.SYSTEM_PROMPT)
            self.assertEqual(factory.call_args.kwargs['http_options'].timeout, 30000)
            context.__aexit__.assert_awaited_once()

    async def test_missing_api_key(self):
        missing_file = MagicMock()
        missing_file.is_file.return_value = False
        with patch.dict(os.environ, {}, clear=True), patch.object(app, 'API_KEY_FILE', missing_file), \
             self.assertRaisesRegex(ValueError, 'GEMINI_API_KEY'):
            await app.get_llm_response('What time is it?')

    async def test_voice_pipeline(self):
        with patch.object(app, 'transcribe_audio', return_value='What time is it?') as transcribe, \
             patch.object(app, 'get_llm_response', new_callable=AsyncMock,
                          return_value='{"name":"display_time","args":[]}') as interpret:
            result = await app.process_input('/tmp/voice.wav')
            self.assertEqual(result, ('What time is it?', '{"name":"display_time","args":[]}', 'Command generated'))
            transcribe.assert_called_once_with('/tmp/voice.wav')
            interpret.assert_awaited_once_with('What time is it?')

    async def test_failure_preserves_transcription_and_clears_json(self):
        with patch.object(app, 'transcribe_audio', return_value='Hello'), \
             patch.object(app, 'get_llm_response', new_callable=AsyncMock, side_effect=ValueError('Invalid JSON')):
            result = await app.process_input('/tmp/voice.wav')
            self.assertEqual(result, ('Hello', '', 'Error: Invalid JSON'))

    async def test_empty_recording_not_sent_to_gemini(self):
        with patch.object(app, 'get_llm_response', new_callable=AsyncMock) as interpret:
            result = await app.process_input(None)
            self.assertEqual(result[1], '')
            self.assertIn('Record audio', result[2])
            interpret.assert_not_awaited()

    async def test_text_pipeline(self):
        with patch.object(app, 'get_llm_response', new_callable=AsyncMock,
                          return_value='{"name":"display_weather","args":[]}'):
            self.assertEqual(await app.process_text('Weather?'),
                             ('Weather?', '{"name":"display_weather","args":[]}', 'Command generated'))


if __name__ == '__main__':
    unittest.main()
