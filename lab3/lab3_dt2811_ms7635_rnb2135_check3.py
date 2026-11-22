from machine import Pin, PWM, I2C, RTC
import time
import ssd1306

# Pin configuration — unchanged.
PIEZO_PIN = 32
BUTTON_A = 12
BUTTON_B = 13
BUTTON_C = 14

DEBOUNCE_MS = 50
BEEP_PERIOD_MS = 300

# OLED.
i2c = I2C(
    0,
    sda=Pin(22),
    scl=Pin(20),
    freq=400000
)
display = ssd1306.SSD1306_I2C(128, 32, i2c)

# Reset the RTC once at startup, never inside the loop.
rtc = RTC()
# year, month, day, weekday, hour, minute, second, subseconds
rtc.datetime((2026, 9, 30, 2, 12, 0, 0, 0))

# Piezo.
piezo_pwm = PWM(Pin(PIEZO_PIN), freq=1000)
piezo_pwm.duty_u16(0)


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

# Mutually exclusive screens: SET, CLOCK, RINGING.
mode = "SET"

alarm_hour = 12
alarm_minute = 1
alarm_enabled = False
last_alarm = None

beep_on = False
last_beep_time = time.ticks_ms()
previous_screen = None

try:
    while True:
        now = time.ticks_ms()

        a_pressed = button_a.pressed()
        b_pressed = button_b.pressed()
        c_pressed = button_c.pressed()

        # Read the advancing RTC every loop.
        year, month, day, weekday, hour, minute, second, _ = rtc.datetime()
        alarm_id = (year, month, day, hour, minute)

        # -----------------------------
        # Handle the current mode
        # -----------------------------

        if mode == "SET":
            if a_pressed:
                alarm_hour = (alarm_hour + 1) % 24

            if b_pressed:
                alarm_minute = (alarm_minute + 1) % 60

            if c_pressed:
                alarm_enabled = True
                mode = "CLOCK"

        elif mode == "CLOCK":
            if (
                alarm_enabled
                and hour == alarm_hour
                and minute == alarm_minute
                and alarm_id != last_alarm
            ):
                last_alarm = alarm_id
                mode = "RINGING"

                beep_on = True
                piezo_pwm.duty_u16(32768)
                last_beep_time = now

        elif mode == "RINGING":
            if a_pressed or b_pressed or c_pressed:
                # Return to the clock without retriggering this minute.
                piezo_pwm.duty_u16(0)
                beep_on = False
                mode = "CLOCK"

            elif time.ticks_diff(now, last_beep_time) >= BEEP_PERIOD_MS:
                # Toggle the sound without blocking the main loop.
                last_beep_time = now
                beep_on = not beep_on
                piezo_pwm.duty_u16(32768 if beep_on else 0)

        # -----------------------------
        # Choose exactly one screen
        # -----------------------------

        if mode == "SET":
            screen = (
                "SET ALARM",
                "{:02d}:{:02d}".format(alarm_hour, alarm_minute),
                "A:SAVE B:M C:H"
            )

        elif mode == "RINGING":
            screen = (
                "!!! ALARM !!!",
                "{:02d}:{:02d}:{:02d}".format(hour, minute, second),
                "Press any button"
            )

        else:
            screen = (
                "{:04d}-{:02d}-{:02d}".format(year, month, day),
                "{:02d}:{:02d}:{:02d}".format(hour, minute, second),
                "Alarm {:02d}:{:02d}".format(alarm_hour, alarm_minute)
            )

        # Update only when visible content changes.
        if screen != previous_screen:
            display.fill(0)

            for text, y in zip(screen, (0, 11, 22)):
                x = max(0, (128 - len(text) * 8) // 2)
                display.text(text, x, y)

            display.show()
            previous_screen = screen

        time.sleep_ms(10)

finally:
    # Silence the piezo if the program is interrupted.
    piezo_pwm.duty_u16(0)