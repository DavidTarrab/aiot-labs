from machine import Pin, I2C, RTC
import time
import ssd1306

DEBOUNCE_MS = 50


from machine import Pin, I2C, RTC, disable_irq, enable_irq
import time
import ssd1306

DEBOUNCE_MS = 50

class DebouncedButton:
    def __init__(self, gpio):
        # Active-low: released = 1, pressed = 0.
        self.pin = Pin(gpio, Pin.IN, Pin.PULL_UP)
        self.stable_state = self.pin.value()
        self.last_change = time.ticks_ms()
        self.pending = False

        # Interrupt on both press and release, including contact bounce.
        self.pin.irq(
            trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING,
            handler=self._on_edge
        )

    def _on_edge(self, pin):
        # Keep the interrupt handler short.
        # Every edge restarts the debounce interval.
        self.last_change = time.ticks_ms()
        self.pending = True

    def pressed(self):
        """Return True once for each debounced button press."""
        pressed_event = False

        # Protect the state shared with the interrupt handler.
        irq_state = disable_irq()
        try:
            if (
                self.pending
                and time.ticks_diff(
                    time.ticks_ms(), self.last_change
                ) >= DEBOUNCE_MS
            ):
                raw = self.pin.value()
                self.pending = False

                if raw != self.stable_state:
                    self.stable_state = raw

                    # Accept releases too, but report only presses.
                    pressed_event = (raw == 0)
        finally:
            enable_irq(irq_state)

        return pressed_event


# Reset the system time on every boot.
rtc = RTC()
# Format: year, month, day, weekday, hour, minute, second, subseconds
rtc.datetime((2026, 9, 30, 2, 12, 0, 0, 0))

i2c = I2C(0, sda=Pin(22), scl=Pin(20), freq=400000)
display = ssd1306.SSD1306_I2C(128, 32, i2c)

button_a = DebouncedButton(12)
button_b = DebouncedButton(13)
button_c = DebouncedButton(14)

previous_time = None

while True:
    # Poll every button each iteration so releases are debounced too.
    increase_hour = button_a.pressed()
    increase_minute = button_b.pressed()
    reset_seconds = button_c.pressed()

    if increase_hour or increase_minute or reset_seconds:
        current = list(rtc.datetime())

        if increase_hour:
            current[4] = (current[4] + 1) % 24

        if increase_minute:
            current[5] = (current[5] + 1) % 60

        if reset_seconds:
            current[6] = 0

        current[7] = 0

        # Change the actual system clock.
        rtc.datetime(tuple(current))

    # Read the clock after applying any button changes.
    year, month, day, weekday, hour, minute, second, _ = rtc.datetime()
    current_time = (year, month, day, hour, minute, second)

    # Redraw only when the displayed date or time changes.
    if current_time != previous_time:
        date_text = "{:04d}-{:02d}-{:02d}".format(year, month, day)
        time_text = "{:02d}:{:02d}:{:02d}".format(hour, minute, second)

        display.fill(0)
        display.text(date_text, 24, 4)
        display.text(time_text, 32, 20)
        display.show()

        previous_time = current_time

    # Poll frequently without blocking for the debounce interval.
    time.sleep_ms(10)