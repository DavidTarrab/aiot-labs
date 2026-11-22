from machine import Pin
import utime
import neopixel

# Power-enable for NeoPixel
pwr = Pin(2, Pin.OUT)
pwr.value(1) # turn on power

builtin_led = Pin(13, Pin.OUT)

builtin_led.value(0)

# SOS = ... --- ...
morse = "... --- ..."

for signal in morse:

    if signal == ".":
        builtin_led.value(1)
        utime.sleep_ms(200)  # DOT

    elif signal == "-":
        builtin_led.value(1)
        utime.sleep_ms(600)  # DASH

    else:
        utime.sleep_ms(400)  # Space between letters

    # Turn LEDs off
    builtin_led.value(0)

    utime.sleep_ms(200)