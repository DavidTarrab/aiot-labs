# Lab 5 checkpoint 4

Checkpoint 3 records speech, transcribes it with Whisper, asks Gemini to interpret it, and displays validated JSON. Checkpoint 4 adds automatic execution of that JSON on the smartwatch.

## Files

- `lab5_dt2811_ms7635_rnb2135_check4.py`: desktop app and TCP client. It imports the checkpoint 3 transcription and interpretation functions, so include `lab5_dt2811_ms7635_rnb2135_check3.py` alongside it.
- `lab5_dt2811_ms7635_rnb2135_check4_server.py`: ESP32 firmware, renamed from the former checkpoint 3 server. It retains the OLED wake fix and the 48-character text limit.
- `lab5_dt2811_ms7635_rnb2135_check4_tests.py`: offline integration checks.

Checkpoint 2 files and `ssd1306.py` are unchanged.

## Setup and use

Copy the checkpoint 4 server and `ssd1306.py` to the ESP32. Configure `WIFI_SSID` and `WIFI_PASSWORD` and run the server, or copy it as `main.py` for startup. Stop any older server before running this one; they use the same TCP port 8080.

The firmware uses OLED SDA 22 / SCL 20, piezo 32, buttons 12/13/14, and the same MicroPython dependencies as checkpoint 2. Location is IP-based; weather comes from Open-Meteo. Synchronous location/weather requests can briefly pause screen refresh and alarm handling. Other successful commands wake the screen after `screen_off`.

Run the desktop app:

```sh
source .venv/bin/activate
python lab5_dt2811_ms7635_rnb2135_check4.py
```

The app uses the same private `.gemini_api_key` file and Gemini/timezone settings as checkpoint 3. Keep the key file out of coursework ZIPs.

Enter the ESP32 IP printed in its REPL. The computer running the app must be able to reach that IP. Click **Sync clock to app local time** once before testing the clock or alarms. Synchronizing clears existing alarms, so do it before setting a new alarm.

Record speech and click **Run voice command**, or type a request and click **Run text command**. Each submission generates, validates, and automatically sends one command; the app shows the transcription, LLM JSON, and smartwatch response. An interpretation or validation error prevents sending. A connection error preserves the transcription and generated JSON for review. Commands are not automatically retried.

For the hardware demonstration, try the clock, screen off followed by a message, a near-future alarm, weather, location, and a short general-knowledge question. Stop a ringing alarm with a board button or a spoken cancellation.

## Verification

```sh
.venv/bin/python -m unittest lab5_dt2811_ms7635_rnb2135_check3_tests lab5_dt2811_ms7635_rnb2135_check4_tests
```

The 15 offline checks cover interpretation and validation plus automatic voice/text dispatch, prevention of invalid sends, and preserving outputs on connection failures. The split was also checked by constructing both Gradio interfaces. Actual microphone and physical ESP32 testing remain necessary.
