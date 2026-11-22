import network
import time
import urequests
import ujson
from machine import Pin, I2C
import ssd1306

WIFI_SSID = "Columbia University"
NTFY_TOPIC = "dt2811-weather-1234"

# Match these GPIO numbers to your actual OLED wiring.
# These defaults are the labeled I2C pins on the HUZZAH32 Feather.
OLED_SDA_PIN = 22
OLED_SCL_PIN = 20
OLED_ADDRESS = 0x3C

WEATHER_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    97: "Heavy thunderstorm",
    96: "Thunderstorm, slight hail",
    99: "Thunderstorm, heavy hail",
}


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        # Output: Connecting to Wi-Fi...
        wlan.connect(WIFI_SSID)
        start = time.ticks_ms()

        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) >= 60_000:
                status = wlan.status()
                wlan.disconnect()
                raise RuntimeError(
                    "Wi-Fi connection timed out. Status: %s" % status
                )
            time.sleep_ms(200)

    ip, subnet, gateway, dns = wlan.ifconfig()
    print("Wi-Fi connected!")
    # Output: Wi-Fi connected!
    print("IP address:", ip)
    # Example output: IP address: 192.168.1.100
    print("Gateway:", gateway)
    # Example output: Gateway: 192.168.1.1
    print("DNS server:", dns)
    # Example output: DNS server: 192.168.1.1
    return wlan


def get_location():
    url = "http://ip-api.com/json?fields=status,message,lat,lon"
    response = None
    try:
        response = urequests.get(url)
        if response.status_code != 200:
            raise RuntimeError(
                "Location API HTTP error: %s" % response.status_code
            )
        data = ujson.loads(response.text)
        if data.get("status") != "success":
            raise RuntimeError(data.get("message", "Location lookup failed"))
        return data["lat"], data["lon"]
    finally:
        if response is not None:
            response.close()


def get_weather(latitude, longitude):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=%.6f&longitude=%.6f"
        "&current=temperature_2m,weather_code"
        "&temperature_unit=fahrenheit"
        % (latitude, longitude)
    )
    response = None
    try:
        response = urequests.get(url)
        if response.status_code != 200:
            raise RuntimeError(
                "Weather API HTTP %s: %s"
                % (response.status_code, response.text)
            )
        data = ujson.loads(response.text)
        if data.get("error"):
            raise RuntimeError(data.get("reason", "Weather lookup failed"))
        current = data["current"]
        temperature = current["temperature_2m"]
        description = WEATHER_DESCRIPTIONS.get(
            current["weather_code"], "Unknown weather"
        )
        return temperature, description
    finally:
        if response is not None:
            response.close()


def send_notification(latitude, longitude, temperature, description):
    if NTFY_TOPIC == "YOUR_UNI-weather-RANDOM_SUFFIX":
        raise ValueError("Set NTFY_TOPIC to your unique topic name first")
    message = (
        "Latitude: %.4f\n"
        "Longitude: %.4f\n"
        "Weather: %.1f F, %s"
        % (latitude, longitude, temperature, description)
    )
    response = None
    try:
        response = urequests.post(
            "https://ntfy.sh/" + NTFY_TOPIC,
            data=message.encode("utf-8"),
            headers={
                "Title": "ESP32 Smartwatch Weather",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )
        if response.status_code != 200:
            raise RuntimeError(
                "ntfy HTTP %s: %s" % (response.status_code, response.text)
            )
        print("Notification published!")
        # Output: Notification published!
    finally:
        if response is not None:
            response.close()


def show_message(display, line1, line2=""):
    display.fill(0)
    display.text(line1, 0, 0)
    display.text(line2, 0, 12)
    display.show()


def show_weather(display, temperature, description):
    # Scroll long descriptions within the 16-character display width.
    scroll_text = description + "   "
    doubled = scroll_text + scroll_text
    position = 0
    while True:
        display.fill(0)
        display.text("Current weather", 0, 0)
        display.text("%.1f F" % temperature, 0, 12)
        if len(description) <= 16:
            display.text(description, 0, 24)
        else:
            display.text(doubled[position:position + 16], 0, 24)
            position = (position + 1) % len(scroll_text)
        display.show()
        time.sleep_ms(300)


def main():
    display = None
    stage = "OLED"
    try:
        i2c = I2C(
            0, sda=Pin(OLED_SDA_PIN), scl=Pin(OLED_SCL_PIN), freq=400_000
        )
        display = ssd1306.SSD1306_I2C(128, 32, i2c, addr=OLED_ADDRESS)

        stage = "Wi-Fi"
        show_message(display, "Connecting Wi-Fi")
        wlan = connect_wifi()

        stage = "Location"
        show_message(display, "Getting location")
        latitude, longitude = get_location()
        print("Latitude: %.4f" % latitude)
        # Example output: Latitude: 40.7128
        print("Longitude: %.4f" % longitude)
        # Example output: Longitude: -74.0060
        display.fill(0)
        display.text("Location", 0, 0)
        display.text("Lat: %.4f" % latitude, 0, 12)
        display.text("Lon: %.4f" % longitude, 0, 24)
        display.show()
        time.sleep(2)

        stage = "Weather"
        show_message(display, "Getting weather")
        temperature, description = get_weather(latitude, longitude)
        print("%.1f F, %s" % (temperature, description))
        # Example output: 77.0 F, Partly cloudy

        # Send once before entering the continuous OLED display loop.
        # A notification failure still allows the weather to be displayed.
        show_message(display, "Sending push")
        try:
            send_notification(latitude, longitude, temperature, description)
        except Exception as error:
            print("Notification error:", error)
            # Example output: Notification error: ntfy HTTP 429: Too many requests
            show_message(display, "Push failed", "Check REPL")
            time.sleep(2)

        stage = "Display"
        show_weather(display, temperature, description)
    except Exception as error:
        print("%s error: %s" % (stage, error))
        # Example output: Location error: Location API HTTP error: 429
        if display is not None:
            show_message(display, stage + " error", "Check REPL")


main()
