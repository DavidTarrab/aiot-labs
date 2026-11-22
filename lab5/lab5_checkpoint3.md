# Lab 5 checkpoint 3

## New files

- `lab5_dt2811_ms7635_rnb2135_check3.py`: standalone desktop app, Whisper transcription, Gemini interpretation, and JSON validation.
- `lab5_dt2811_ms7635_rnb2135_check3_tests.py`: offline regression checks.

Checkpoint 2 files and the shared `ssd1306.py` are unchanged. The new desktop app does not import earlier checkpoint apps. Checkpoint 3 does not require an ESP32 server or connection.

## Run

The Gemini SDK (`google-genai`) has been installed in `.venv`. Your supplied key is configured in `.gemini_api_key`, which is readable only by your user and excluded by `.gitignore`. The app loads it automatically. Launch with:

```sh
source .venv/bin/activate
python lab5_dt2811_ms7635_rnb2135_check3.py
```

To use a different key from [Google AI Studio](https://aistudio.google.com/app/api-keys), you can override the local file in the terminal that launches the app. To avoid displaying the key while entering it, use these zsh commands:

```sh
source .venv/bin/activate
read -s 'GEMINI_API_KEY?Gemini API key: '
export GEMINI_API_KEY
python lab5_dt2811_ms7635_rnb2135_check3.py
```

Keep `.gemini_api_key` out of coursework ZIPs. Neither the source nor the public Gradio UI contains the key. Environment variables take precedence over the local file; `GOOGLE_API_KEY` is also accepted if `GEMINI_API_KEY` is unset.

The default model is `gemini-3.5-flash-lite`, matching the lab handout. Set `GEMINI_MODEL` before launch to use another model supported by your account. Both the Gemini prompt and the clock-sync command use `WATCH_TIMEZONE`, defaulting to `America/New_York`.

Use the **Voice input** tab to record and click **Transcribe and interpret**, or the **Text input** tab to test requests without recording. The app displays the transcription/request, validated LLM JSON, and a status. Failed requests retain the transcription, clear the command field, and show an error.

Checkpoint 3 displays generated JSON for review. Run `lab5_dt2811_ms7635_rnb2135_check4.py` for automatic execution on the smartwatch; see `lab5_checkpoint4.md` for its server and setup.

## Gemini command interface

The system prompt describes every command, the 24-hour clock format, timestamp conversion for relative intervals, the current local date/time, short general-knowledge answers, and ambiguity handling. Gemini is configured for structured JSON output. Local validation rejects extra keys, unsupported functions, incorrect argument counts, wrong types, out-of-range alarm times, and messages exceeding the OLED limit.

| Function | Arguments |
| --- | --- |
| `screen_on` / `screen_off` | `[]` |
| `display_time` | `[]` |
| `display_text` | `[text]`, 1–48 printable ASCII characters |
| `set_alarm` | `[hour, minute, second]`, integers in ranges 0–23, 0–59, 0–59 |
| `display_location` / `display_weather` | `[]` |
| `stop_alarm` | `[]` |

The generated commands target the interface documented in checkpoint 2. Gemini does not generate clock-sync commands. A valid alarm timestamp refers to its next occurrence; dated or recurring alarms and intervals of 24 hours or longer are unsupported and should produce a short clarification.

## Demonstration and checks

Try these spoken and typed inputs. Assess that the generated command matches the request, and review the displayed JSON:

| Request | Expected command |
| --- | --- |
| What time is it? | `display_time`, `[]` |
| Turn off the screen / Wake the screen | `screen_off` / `screen_on`, `[]` |
| Set an alarm for 4:30 PM | `set_alarm`, `[16,30,0]` |
| Set an alarm for midnight / noon | `set_alarm`, `[0,0,0]` / `[12,0,0]` |
| Set an alarm in five minutes | `set_alarm`, timestamp five minutes after the supplied current local time |
| What's the weather like? | `display_weather`, `[]` |
| Where am I? | `display_location`, `[]` |
| Show hello world | `display_text`, `["hello world"]` |
| How old is Columbia University? | `display_text`, short answer using the supplied date |
| Stop the buzzer | `stop_alarm`, `[]` |
| Set an alarm | `display_text`, short request for a time |

Run offline checks with:

```sh
.venv/bin/python lab5_dt2811_ms7635_rnb2135_check3_tests.py
```

All 10 checkpoint 3 offline checks passed. They cover the voice/text pipelines, SDK request configuration with mocked replies, timestamp-context midnight rollover, valid/invalid JSON commands.

Live Gemini checks with your configured key also passed for the clock, screen on/off, 4:30 PM alarm, five-minute alarm across midnight, weather, location, alarm cancellation, missing-time clarification, and a general-knowledge answer. The age prompt was refined to request an age rather than just a founding year; a follow-up live check returned 272 years for Columbia University using the supplied October 2026 date. These checks used typed requests, not microphone recordings. Microphone testing remains. Actual ESP32 execution and its hardware demonstration are covered by checkpoint 4.

References: [Gemini structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en), [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).
