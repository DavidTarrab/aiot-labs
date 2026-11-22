"""Offline checks for automatic checkpoint 4 execution."""
import unittest
from unittest.mock import AsyncMock, patch

import lab5_dt2811_ms7635_rnb2135_check4 as app


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_voice_command_sent_automatically(self):
        generated = ('What time is it?', '{"name":"display_time","args":[]}', 'Command generated')
        with patch.object(app, 'interpret_audio', new_callable=AsyncMock, return_value=generated), \
             patch.object(app, 'SmartwatchClient') as client:
            client.return_value.send_json.return_value = 'Displaying the live clock'
            result = await app.process_input('/tmp/voice.wav', '192.168.1.10', 8080)
            self.assertEqual(result, (generated[0], generated[1], 'Displaying the live clock'))
            client.return_value.send_json.assert_called_once_with({'name': 'display_time', 'args': []})

    async def test_text_command_sent_automatically(self):
        generated = ('Screen off', '{"name":"screen_off","args":[]}', 'Command generated')
        with patch.object(app, 'interpret_text', new_callable=AsyncMock, return_value=generated), \
             patch.object(app, 'SmartwatchClient') as client:
            client.return_value.send_json.return_value = 'Screen off'
            result = await app.process_text('Screen off', '192.168.1.10', 8080)
            self.assertEqual(result[2], 'Screen off')
            client.return_value.send_json.assert_called_once_with({'name': 'screen_off', 'args': []})

    async def test_interpretation_error_not_sent(self):
        with patch.object(app, 'SmartwatchClient') as client:
            result = await app.execute_interpretation(('Speech', '', 'Error: Invalid JSON'), 'host', 8080)
            self.assertEqual(result, ('Speech', '', 'Error: Invalid JSON'))
            client.assert_not_called()

    async def test_invalid_json_not_sent(self):
        with patch.object(app, 'SmartwatchClient') as client:
            result = await app.execute_interpretation(('Alarm', '{"name":"set_alarm","args":[25,0,0]}', 'OK'), 'host', 8080)
            self.assertTrue(result[2].startswith('Error:'))
            client.assert_not_called()

    async def test_connection_error_keeps_transcription_and_json(self):
        generated = ('Clock', '{"name":"display_time","args":[]}', 'Command generated')
        with patch.object(app, 'SmartwatchClient', side_effect=OSError('Connection refused')):
            result = await app.execute_interpretation(generated, 'host', 8080)
            self.assertEqual(result[:2], generated[:2])
            self.assertIn('Connection refused', result[2])


if __name__ == '__main__':
    unittest.main()
