"""Checkpoint 2 ESP32 firmware. Copy alongside ssd1306.py and run on MicroPython.

TCP port 8080: one UTF-8 JSON command followed by a newline per connection.
Replies: {"ok": true, "result": "..."} or {"ok": false, "error": "..."}.
See lab5_checkpoint2.md for the command reference and setup instructions.
"""
import uasyncio as asyncio
import ujson as json
import network
import time
import urequests
from machine import Pin, I2C, RTC, PWM
import ssd1306

WIFI_SSID = "Columbia University"
WIFI_PASSWORD = ""  # Leave empty for the open network used in lab 4.
SERVER_PORT = 8080
OLED_SDA_PIN = 22
OLED_SCL_PIN = 20
PIEZO_PIN = 32
BUTTON_PINS = (12, 13, 14)
MAX_COMMAND_BYTES = 2048

# Same weather codes and Fahrenheit units as lab 4.
WEATHER_DESCRIPTIONS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 56: "Light freezing drizzle", 57: "Freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Heavy showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm/hail", 99: "Thunderstorm/hail",
}


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("%s must be an integer from %s to %s" % (label, low, high))
    return value


def get_json(url):
    response = None
    try:
        response = urequests.get(url, timeout=8)
        if response.status_code != 200:
            raise RuntimeError("API HTTP error: %s" % response.status_code)
        return json.loads(response.text)
    finally:
        if response is not None:
            response.close()


def get_location():
    data = get_json("http://ip-api.com/json?fields=status,message,lat,lon")
    if data.get("status") != "success":
        raise RuntimeError(data.get("message", "Location lookup failed"))
    return data["lat"], data["lon"]


def get_weather(latitude, longitude):
    data = get_json(
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=%.6f&longitude=%.6f"
        "&current=temperature_2m,weather_code&temperature_unit=fahrenheit"
        % (latitude, longitude)
    )
    current = data["current"]
    return current["temperature_2m"], WEATHER_DESCRIPTIONS.get(
        current["weather_code"], "Unknown weather"
    )


class Smartwatch:
    def __init__(self):
        i2c = I2C(0, sda=Pin(OLED_SDA_PIN), scl=Pin(OLED_SCL_PIN), freq=400000)
        self.display = ssd1306.SSD1306_I2C(128, 32, i2c)
        self.rtc = RTC()
        self.piezo = PWM(Pin(PIEZO_PIN), freq=1000)
        self.piezo.duty_u16(0)
        self.buttons = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in BUTTON_PINS]
        self.screen_enabled = True
        self.clock_synced = False
        self.mode = "message"
        self.lines = ("Lab 5 ready", "Sync clock", "from desktop")
        self.previous_screen = None
        self.alarm_due = None
        self.ringing_since = None
        self.handlers = {
            "screen_on": (self.screen_on, 0),
            "screen_off": (self.screen_off, 0),
            "display_time": (self.display_time, 0),
            "display_text": (self.display_text, 1),
            "set_alarm": (self.set_alarm, 3),
            "display_location": (self.display_location, 0),
            "display_weather": (self.display_weather, 0),
            "set_time": (self.set_time, 6),
            "stop_alarm": (self.stop_alarm, 0),
        }

    def screen_on(self):
        # Older copies of the lab's I2C driver have a no-op poweron().
        # Send SSD1306 DISPLAY ON directly so those drivers work too.
        self.display.write_cmd(0xAF)
        self.screen_enabled = True
        self.previous_screen = None
        return "Screen on"

    def screen_off(self):
        self.display.poweroff()
        self.screen_enabled = False
        return "Screen off"

    def display_time(self):
        if not self.clock_synced:
            raise ValueError("Sync the clock with set_time first")
        self.mode = "clock"
        return "Displaying the live clock"

    def display_text(self, text):
        if not isinstance(text, str) or not text or len(text) > 64:
            raise ValueError("Text must contain 1 to 64 characters")
        if any(ord(char) < 32 or ord(char) > 126 for char in text):
            raise ValueError("OLED text must use printable ASCII characters")
        self.mode = "message"
        self.lines = tuple(text[index:index + 16] for index in range(0, len(text), 16))
        return "Displaying: " + text

    def set_time(self, year, month, day, hour, minute, second):
        integer(year, 2000, 2099, "Year")
        integer(month, 1, 12, "Month")
        days = (31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30,
                31, 31, 30, 31, 30, 31)
        integer(day, 1, days[month - 1], "Day")
        integer(hour, 0, 23, "Hour")
        integer(minute, 0, 59, "Minute")
        integer(second, 0, 59, "Second")
        stamp = time.mktime((year, month, day, hour, minute, second, 0, 0))
        weekday = time.localtime(stamp)[6]
        self.rtc.datetime((year, month, day, weekday, hour, minute, second, 0))
        self.clock_synced = True
        self.alarm_due = None
        self.stop_alarm()
        return "Clock synced to desktop local time; previous alarm cleared"

    def set_alarm(self, hour, minute, second):
        integer(hour, 0, 23, "Hour")
        integer(minute, 0, 59, "Minute")
        integer(second, 0, 59, "Second")
        if not self.clock_synced:
            raise ValueError("Sync the clock with set_time first")
        now = time.time()
        today = time.localtime(now)
        due = time.mktime((today[0], today[1], today[2], hour, minute, second, 0, 0))
        if due <= now:
            due += 86400
        self.stop_alarm()
        self.alarm_due = due
        return "Alarm set for %02d:%02d:%02d (next occurrence)" % (hour, minute, second)

    def stop_alarm(self):
        self.alarm_due = None
        self.ringing_since = None
        self.piezo.duty_u16(0)
        return "Alarm stopped and cleared"

    def display_location(self):
        latitude, longitude = get_location()
        self.mode = "message"
        self.lines = ("Location", "Lat: %.4f" % latitude, "Lon: %.4f" % longitude)
        return "Latitude: %.4f, longitude: %.4f" % (latitude, longitude)

    def display_weather(self):
        latitude, longitude = get_location()
        temperature, description = get_weather(latitude, longitude)
        self.mode = "message"
        self.lines = ("Current weather", "%.1f F" % temperature,
                      description[:16], description[16:32])
        return "%.1f F, %s" % (temperature, description)

    def execute(self, command):
        if not isinstance(command, dict) or set(command) != {"name", "args"}:
            raise ValueError('Use {"name": "function_name", "args": [...]}')
        name, args = command["name"], command["args"]
        if not isinstance(name, str) or name not in self.handlers:
            raise ValueError("Unknown command name")
        function, count = self.handlers[name]
        if not isinstance(args, list) or len(args) != count:
            raise ValueError("%s requires %s arguments" % (name, count))
        result = function(*args)
        # A successful command wakes the OLED unless it explicitly turns it off.
        if name != "screen_off" and not self.screen_enabled:
            self.screen_on()
        return result

    def update(self):
        now_ms = time.ticks_ms()
        if self.alarm_due is not None and time.time() >= self.alarm_due:
            self.alarm_due = None
            self.ringing_since = now_ms
        if self.ringing_since is not None:
            elapsed = time.ticks_diff(now_ms, self.ringing_since)
            if elapsed >= 10000 or any(button.value() == 0 for button in self.buttons):
                self.stop_alarm()
            else:
                self.piezo.duty_u16(32768 if (elapsed // 300) % 2 == 0 else 0)
        if self.ringing_since is not None:
            lines = ("!!! ALARM !!!", "Press any button", "to stop")
        elif self.mode == "clock":
            year, month, day, _, hour, minute, second, _ = self.rtc.datetime()
            lines = ("%04d-%02d-%02d" % (year, month, day),
                     "%02d:%02d:%02d" % (hour, minute, second),
                     "Alarm set" if self.alarm_due is not None else "Alarm off")
        else:
            lines = self.lines
        if self.screen_enabled and lines != self.previous_screen:
            self.display.fill(0)
            for index, line in enumerate(lines):
                self.display.text(line, 0, index * 8)
            self.display.show()
            self.previous_screen = lines


async def read_command(reader):
    data = bytearray()
    while True:
        chunk = await reader.read(128)
        if not chunk:
            raise ValueError("Command must end with a newline")
        data.extend(chunk)
        if len(data) > MAX_COMMAND_BYTES:
            raise ValueError("Command exceeds 2048 bytes")
        if b"\n" in data:
            line, remainder = bytes(data).split(b"\n", 1)
            if remainder.strip():
                raise ValueError("Send only one command per connection")
            return json.loads(line.decode("utf-8"))


async def handle_client(reader, writer, watch):
    try:
        try:
            command = await asyncio.wait_for(read_command(reader), 5)
            result = watch.execute(command)
            watch.update()
            reply = {"ok": True, "result": result}
        except asyncio.TimeoutError:
            reply = {"ok": False, "error": "Command timed out"}
        except Exception as error:
            reply = {"ok": False, "error": str(error)}
        writer.write((json.dumps(reply) + "\n").encode("utf-8"))
        await asyncio.wait_for(writer.drain(), 5)
    except OSError as error:
        print("Client disconnected:", error)
    except asyncio.TimeoutError:
        print("Reply timed out")
    finally:
        writer.close()
        await writer.wait_closed()


async def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        if WIFI_PASSWORD:
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        else:
            wlan.connect(WIFI_SSID)
        started = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), started) >= 60000:
                wlan.disconnect()
                raise RuntimeError("Wi-Fi connection timed out")
            await asyncio.sleep_ms(200)
    print("ESP32 IP:", wlan.ifconfig()[0])
    return wlan


async def main():
    watch = Smartwatch()
    server = None
    try:
        watch.update()
        await connect_wifi()
        async def client_connected(reader, writer):
            await handle_client(reader, writer, watch)
        server = await asyncio.start_server(client_connected, "0.0.0.0", SERVER_PORT)
        print("JSON command server listening on port", SERVER_PORT)
        while True:
            watch.update()
            await asyncio.sleep_ms(50)
    finally:
        watch.stop_alarm()
        if server is not None:
            server.close()
            await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
