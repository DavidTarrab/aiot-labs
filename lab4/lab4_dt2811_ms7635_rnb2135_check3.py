import network
import time

WIFI_SSID = "Columbia University"


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


wlan = connect_wifi()

import urequests
import ujson


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
            raise RuntimeError(
                data.get("message", "Location lookup failed")
            )

        return data["lat"], data["lon"]

    finally:
        if response is not None:
            response.close()


# Show a loading message on the 128 x 32 OLED.
display.fill(0)
display.text("Getting location", 0, 0)
display.show()

try:
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

except Exception as error:
    print("Location error:", error)
    # Example output: Location error: Location API HTTP error: 429

    display.fill(0)
    display.text("Location error", 0, 0)
    display.text("Check connection", 0, 12)
    display.show()
  
import time

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
        data = ujson.loads(response.text)

        if response.status_code != 200:
            raise RuntimeError(
                "Weather API HTTP %s: %s"
                % (
                    response.status_code,
                    data.get("reason", "Unknown error"),
                )
            )

        current = data["current"]
        temperature = current["temperature_2m"]
        code = current["weather_code"]

        descriptions = {
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
            96: "Thunderstorm, slight hail",
            99: "Thunderstorm, heavy hail",
        }

        description = descriptions.get(code, "Unknown weather")
        return temperature, description

    finally:
        if response is not None:
            response.close()


def show_weather(temperature, description):
    # The 128-pixel display fits 16 characters per line.
    # Scroll longer descriptions so the full text remains readable.
    text = description
    scroll_text = text + "   "
    position = 0

    while True:
        display.fill(0)
        display.text("Current weather", 0, 0)
        display.text("%.1f F" % temperature, 0, 12)

        if len(text) <= 16:
            display.text(text, 0, 24)
        else:
            doubled = scroll_text + scroll_text
            display.text(doubled[position:position + 16], 0, 24)
            position = (position + 1) % len(scroll_text)

        display.show()
        time.sleep_ms(300)


try:
    display.fill(0)
    display.text("Getting location", 0, 0)
    display.show()

    latitude, longitude = get_location()

    display.fill(0)
    display.text("Getting weather", 0, 0)
    display.show()

    temperature, description = get_weather(latitude, longitude)

    print("%.1f F, %s" % (temperature, description))
    # Example output: 25.0 C, scattered clouds

    show_weather(temperature, description)

except Exception as error:
    print("Weather error:", error)
    # Example output: Weather error: Weather API HTTP 401: Invalid API key

    display.fill(0)
    display.text("Weather error", 0, 0)
    display.text("Check REPL", 0, 12)
    display.show()
