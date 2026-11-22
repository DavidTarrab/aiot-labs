from machine import Pin, PWM, I2C, RTC, ADC
import time
import ssd1306

# Pin configuration — unchanged.
PIEZO_PIN = 32
BUTTON_A = 12
BUTTON_B = 13
BUTTON_C = 14
LIGHT_SENSOR_PIN = 26

DEBOUNCE_MS = 50
BEEP_PERIOD_MS = 300
SAMPLE_PERIOD_MS = 100

ADC_MIN = 3500
ADC_MAX = 15000

CONTRAST_MIN = 5
CONTRAST_MAX = 255

# OLED.
i2c = I2C(
    0,
    sda=Pin(22),
    scl=Pin(20),
    freq=400000
)
display = ssd1306.SSD1306_I2C(128, 32, i2c)

# Set the RTC once at startup.
rtc = RTC()
# year, month, day, weekday, hour, minute, second, subseconds
rtc.datetime((2026, 9, 30, 2, 12, 0, 0, 0))

# Piezo.
piezo_pwm = PWM(Pin(PIEZO_PIN), freq=1000)
piezo_pwm.duty_u16(0)

# Light sensor.
light_sensor = ADC(Pin(LIGHT_SENSOR_PIN))
light_sensor.atten(ADC.ATTN_11DB)


class DebouncedButton:
    def __init__(self, gpio):
        self.pin = Pin(gpio, Pin.IN, Pin.PULL_UP)
        self.last_raw = self.pin.value()
        self.stable_state = self.last_raw
        self.last_change = time.ticks_ms()

    def pressed(self):
        """Return True once per stable active-low press."""
        raw = self.pin.value()
        now = time.ticks_ms()

        if raw != self.last_raw:
            self.last_raw = raw
            self.last_change = now

        if (
            raw != self.stable_state
            and time.ticks_diff(now, self.last_change) >= DEBOUNCE_MS
        ):
            self.stable_state = raw
            return raw == 0

        return False


button_a = DebouncedButton(BUTTON_A)
button_b = DebouncedButton(BUTTON_B)
button_c = DebouncedButton(BUTTON_C)

mode = "SET"

alarm_hour = 0
alarm_minute = 0
alarm_selected = False
alarm_enabled = False
last_alarm = None

beep_on = False
last_beep_time = time.ticks_ms()

raw_light = 0
light_percent = 0
previous_contrast = None
previous_screen = None

last_sample_time = time.ticks_add(
    time.ticks_ms(), -SAMPLE_PERIOD_MS
)

try:
    while True:
        now = time.ticks_ms()

        a_pressed = button_a.pressed()
        b_pressed = button_b.pressed()
        c_pressed = button_c.pressed()

        # Light sensing and automatic contrast in every mode.
        if time.ticks_diff(now, last_sample_time) >= SAMPLE_PERIOD_MS:
            last_sample_time = now
            raw_light = light_sensor.read_u16()

            light_level = (
                (raw_light - ADC_MIN) / (ADC_MAX - ADC_MIN)
            )
            light_level = max(0.0, min(1.0, light_level))
            light_percent = int(light_level * 100)

            contrast = int(
                CONTRAST_MIN
                + light_level * (CONTRAST_MAX - CONTRAST_MIN)
            )

            if contrast != previous_contrast:
                display.contrast(contrast)
                previous_contrast = contrast

        # Handle buttons for the current screen.
        if mode == "SET":
            if a_pressed or b_pressed:
                if not alarm_selected:
                    # Begin editing from the current hour/minute.
                    current = rtc.datetime()
                    alarm_hour = current[4]
                    alarm_minute = current[5]
                    alarm_selected = True

                if a_pressed:
                    alarm_hour = (alarm_hour + 1) % 24

                if b_pressed:
                    alarm_minute = (alarm_minute + 1) % 60

            if c_pressed:
                # Saving --:-- means no alarm.
                alarm_enabled = alarm_selected
                mode = "CLOCK"

        elif mode == "CLOCK":
            if a_pressed or b_pressed:
                current = list(rtc.datetime())

                if a_pressed:
                    current[4] = (current[4] + 1) % 24

                if b_pressed:
                    current[5] = (current[5] + 1) % 60

                current[7] = 0
                rtc.datetime(tuple(current))

            if c_pressed:
                # Start a fresh alarm selection.
                alarm_selected = False
                alarm_enabled = False
                mode = "SET"

        elif mode == "RINGING":
            if a_pressed or b_pressed or c_pressed:
                piezo_pwm.duty_u16(0)
                beep_on = False
                alarm_enabled = False
                alarm_selected = False
                mode = "SET"

            elif time.ticks_diff(now, last_beep_time) >= BEEP_PERIOD_MS:
                last_beep_time = now
                beep_on = not beep_on
                piezo_pwm.duty_u16(32768 if beep_on else 0)

        # Read the RTC after any clock adjustments.
        year, month, day, weekday, hour, minute, second, _ = rtc.datetime()
        alarm_id = (year, month, day, hour, minute)

        # Check the alarm only on the clock screen.
        if (
            mode == "CLOCK"
            and alarm_enabled
            and hour == alarm_hour
            and minute == alarm_minute
            and alarm_id != last_alarm
        ):
            last_alarm = alarm_id
            mode = "RINGING"
            beep_on = True
            piezo_pwm.duty_u16(32768)
            last_beep_time = now

        # Select exactly one screen.
        if mode == "SET":
            alarm_text = (
                "{:02d}:{:02d}".format(alarm_hour, alarm_minute)
                if alarm_selected else "--:--"
            )

            screen = (
                "SET ALARM",
                alarm_text,
                "A:Save B:Minute",
                "C:Hour"
            )

        elif mode == "RINGING":
            screen = (
                "!!! ALARM !!!",
                "{:02d}:{:02d}:{:02d}".format(hour, minute, second),
                "Press any button",
                "to set new alarm"
            )

        else:
            alarm_text = (
                "Alarm {:02d}:{:02d}".format(alarm_hour, alarm_minute)
                if alarm_enabled else "Alarm OFF"
            )

            screen = (
                "{:02d}:{:02d}:{:02d}".format(hour, minute, second),
                alarm_text,
                "ADC: {}".format(raw_light),
                "Light: {}%".format(light_percent)
            )

        if screen != previous_screen:
            display.fill(0)

            for text, y in zip(screen, (0, 8, 16, 24)):
                x = max(0, (128 - len(text) * 8) // 2)
                display.text(text, x, y)

            display.show()
            previous_screen = screen

        time.sleep_ms(10)

finally:
    piezo_pwm.duty_u16(0)