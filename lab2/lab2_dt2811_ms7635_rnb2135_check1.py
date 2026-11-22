from machine import Pin, PWM, ADC
import time

LED_PIN = 15
PIEZO_PIN = 32
LIGHT_SENSOR_PIN = 26

# -----------------------------
# PWM setup
# -----------------------------

led_pwm = PWM(Pin(LED_PIN), freq=1000)
piezo_pwm = PWM(Pin(PIEZO_PIN), freq=440)

# -----------------------------
# ADC setup
# -----------------------------

light_sensor = ADC(Pin(LIGHT_SENSOR_PIN))

# Allows ESP32 ADC to measure a larger voltage range
light_sensor.atten(ADC.ATTN_11DB)

# Start outputs off
led_pwm.duty_u16(0)
piezo_pwm.duty_u16(0)


def set_led_brightness(brightness):
    """
    brightness: 0.0 to 1.0
    """
    brightness = max(0.0, min(1.0, brightness))

    duty = int(brightness * 65535)
    led_pwm.duty_u16(duty)


def set_piezo(pitch, volume=0.5):
    """
    pitch: frequency in Hz
    volume: 0.0 to 1.0
    """
    volume = max(0.0, min(1.0, volume))

    piezo_pwm.freq(int(pitch))

    duty = int(volume * 65535)
    piezo_pwm.duty_u16(duty)


def map_value(value, in_min, in_max, out_min, out_max):
    """
    Maps a value from one range to another.
    """
    return (
        (value - in_min)
        * (out_max - out_min)
        / (in_max - in_min)
        + out_min
    )


# -----------------------------
# Main loop
# -----------------------------

while True:

    # ADC returns a value from 0 to 65535
    light_raw = light_sensor.read_u16()

    # Normalize to 0.0 - 1.0
    light_level = light_raw / 65535

    # Use light level directly as LED brightness
    set_led_brightness(light_level)

    # Map light level to piezo frequency:
    # dark  -> 200 Hz
    # bright -> 2000 Hz
    pitch = map_value(light_level, 0.0, 1.0, 200, 2000)

    set_piezo(pitch, 0.5)

    print(
        "ADC:", light_raw,
        "Light:", light_level,
        "Pitch:", pitch
    )
    # Output example:
    # ADC: 32768 Light: 0.5000076295109483 Pitch: 1100.0137331197068

    # 100 ms between samples = 10 samples per second
    time.sleep_ms(100)