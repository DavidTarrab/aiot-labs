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