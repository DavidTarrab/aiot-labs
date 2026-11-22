# Lab 5 checkpoints 1 and 2

## Files and setup

- `lab5_dt2811_ms7635_rnb2135_check2.py`: desktop Gradio app and reusable TCP client.
- `lab5_dt2811_ms7635_rnb2135_check2_server.py`: ESP32 MicroPython firmware.
- `ssd1306.py`: OLED driver copied from lab 3.
- `lab5_dt2811_ms7635_rnb2135_check1.py`: existing Whisper transcription callback used by the desktop app.

Copy the server and `ssd1306.py` onto the ESP32 with your usual MicroPython editor. Run the server (or rename it to `main.py` on the board for startup). It uses your prior OLED wiring, SDA 22/SCL 20, a 128×32 display at address 0x3C, piezo 32, and active-low buttons 12/13/14. Adjust the constants if your hardware differs. Set `WIFI_SSID`/`WIFI_PASSWORD` in the server. The default is the open Columbia University network from lab 4.

The firmware needs `uasyncio`, `ujson`, `network`, `machine`, and `urequests`. The first four are normally built into ESP32 MicroPython; use the same `urequests` installation as lab 4, with support for its `timeout` argument. If needed, install the current MicroPython `requests` package and import it as `urequests` in the server.

The board prints its IP and listens on TCP port 8080. The computer must be able to reach this address. If campus Wi-Fi blocks connections between devices, connect both to the same private Wi-Fi/hotspot and update the server's Wi-Fi settings.

On the computer, run:

```sh
source .venv/bin/activate
python lab5_dt2811_ms7635_rnb2135_check2.py
```

Desktop dependencies are `gradio`, `openai-whisper`, and `truststore`, already present in the lab environment. FFmpeg is installed in `.venv/bin`; activate the environment so Whisper finds it. Both local and temporary public Gradio URLs are enabled. The app connects to the ESP32 from the computer running Python, including when the public app URL is opened on a phone.

Use the **Voice transcription** tab for checkpoint 1. Use **Smartwatch commands** for checkpoint 2. Enter the ESP32 IP, click **Sync clock to desktop local time**, choose a JSON example, and click **Send command**. Voice input is transcribed only at this checkpoint; natural-language command interpretation comes later in the spec.

## JSON command reference

Each TCP connection carries one UTF-8 JSON object, terminated by a newline. Replies are also newline-terminated JSON: `{"ok": true, "result": "..."}` or `{"ok": false, "error": "..."}`. Requests must have exactly `name` and `args`; only the listed functions are dispatched. Invalid names, counts, types, ranges, malformed JSON, oversized requests, incomplete requests, and API failures return errors.

| Function | Arguments | Behavior / example |
| --- | --- | --- |
| `screen_on` | `[]` | Powers on the OLED and redraws its current content. |
| `screen_off` | `[]` | Powers off the OLED; the clock and alarm continue running. Any other successful command turns the OLED back on. |
| `display_time` | `[]` | Displays live date and HH:MM:SS from the advancing RTC. Sync first. |
| `display_text` | `[text]` | Displays 1–64 printable ASCII characters, wrapped over four 16-character lines. |
| `set_alarm` | `[hour, minute, second]` | Sets a one-shot alarm at the next occurrence of this 24-hour local timestamp. Example: `{"name":"set_alarm","args":[16,30,0]}`. Integers only: hour 0–23; minute/second 0–59. |
| `display_location` | `[]` | Fetches IP-based latitude/longitude using the lab 4 API and displays both. This is network geolocation, not GPS. |
| `display_weather` | `[]` | Fetches current-location temperature in Fahrenheit and weather description from Open-Meteo, as in lab 4. |
| `set_time` | `[year, month, day, hour, minute, second]` | Sets the RTC to the desktop's local calendar time, validates the date, and clears any old alarm. The Sync button creates this command. |
| `stop_alarm` | `[]` | Silences and clears the alarm. Any physical button also stops a ringing alarm. |

The RTC advances independently of commands. The alarm uses a due timestamp so it still triggers if a loop iteration misses the exact second. It beeps in 300 ms intervals for up to 10 seconds and shows an alarm screen if the OLED is on. Location/weather HTTP calls are synchronous with 8-second socket timeouts; screen refresh and alarm handling can pause during those calls and resume afterward. Screen commands preserve the selected display mode.

## Checkpoint 2 demonstration

1. Sync the clock. Send `display_time` and confirm the seconds advance while the server is idle.
2. Send `screen_off`, confirm the OLED is off, then `display_time`, confirming the OLED wakes and time has continued advancing. Repeat with `display_text` to confirm it wakes and shows the new message.
3. Send `display_text` with a message and confirm wrapping on the OLED.
4. Set an alarm about 10 seconds ahead using the desktop client below. Confirm the buzzer sounds, then silence it with a board button or `stop_alarm`.
5. Send `display_location` and `display_weather`; compare the OLED with the returned result.
6. Test errors: `{"name":"unknown","args":[]}`, `{"name":"set_alarm","args":[25,0,0]}`, and `{"name":"screen_on","args":[1]}`. Confirm errors are returned and the server still accepts valid commands.

For standalone Python client testing:

```python
from datetime import datetime, timedelta
from lab5_dt2811_ms7635_rnb2135_check2 import SmartwatchClient

watch = SmartwatchClient("ESP32_IP_HERE")
print(watch.sync_time())
print(watch.screen_on())
print(watch.display_time())
print(watch.display_text("Hello smartwatch!"))
alarm = datetime.now() + timedelta(seconds=10)
print(watch.set_alarm(alarm.hour, alarm.minute, alarm.second))
# Wait for the alarm, then press a physical button or call watch.stop_alarm().
print(watch.display_location())
print(watch.display_weather())
```

Hardware demonstration requires the physical ESP32; offline tests cannot verify wiring, audio output, campus connectivity, or the live external APIs.

Implementation references: [MicroPython asyncio](https://docs.micropython.org/en/latest/library/asyncio.html), [ESP32 RTC and networking](https://docs.micropython.org/en/latest/esp32/quickref.html), and [Open-Meteo](https://open-meteo.com/en/docs).
