from machine import Pin, I2C, ADC
import time
import ssd1306

LIGHT_SENSOR_PIN = 26
SAMPLE_PERIOD_MS = 100

# Calibrated range: dim -> bright.
ADC_MIN = 3500
ADC_MAX = 15000

CONTRAST_MIN = 5
CONTRAST_MAX = 255

# OLED setup.
i2c = I2C(0, sda=Pin(22), scl=Pin(20), freq=400000)
display = ssd1306.SSD1306_I2C(128, 32, i2c)

# Light sensor setup.
light_sensor = ADC(Pin(LIGHT_SENSOR_PIN))
light_sensor.atten(ADC.ATTN_11DB)

previous_contrast = None

while True:
    raw = light_sensor.read_u16()

    # Convert the calibrated reading to 0.0-1.0.
    light_level = (raw - ADC_MIN) / (ADC_MAX - ADC_MIN)
    light_level = max(0.0, min(1.0, light_level))

    light_percent = int(light_level * 100)

    # Dim room -> dim display; bright room -> bright display.
    contrast = int(
        CONTRAST_MIN
        + light_level * (CONTRAST_MAX - CONTRAST_MIN)
    )

    if contrast != previous_contrast:
        display.contrast(contrast)
        previous_contrast = contrast

    display.fill(0)
    display.text("ADC: {}".format(raw), 0, 4)
    display.text("Light: {}%".format(light_percent), 0, 20)
    display.show()

    time.sleep_ms(SAMPLE_PERIOD_MS)