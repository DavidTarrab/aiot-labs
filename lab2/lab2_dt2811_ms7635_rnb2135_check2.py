from machine import Pin
import time

BUTTON_PIN = 33
DEBOUNCE_MS = 50

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)

# Last confirmed stable state
stable_state = button.value()

# Information recorded by the interrupt
candidate_state = stable_state
last_irq_time = 0
debounce_pending = False


def button_irq(pin):
    global candidate_state
    global last_irq_time
    global debounce_pending

    # Record the newest state and restart the debounce timer.
    # If the button bounces, this gets called again and the
    # 50 ms timer effectively starts over.
    candidate_state = pin.value()
    last_irq_time = time.ticks_ms()
    debounce_pending = True


# Generate interrupts for both press and release
button.irq(
    trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
    handler=button_irq
)


while True:
    if debounce_pending:

        # Has the input gone DEBOUNCE_MS without another edge?
        if time.ticks_diff(time.ticks_ms(), last_irq_time) >= DEBOUNCE_MS:

            debounce_pending = False

            # Read the pin again to make sure it is actually stable
            current_state = button.value()

            # Only report if the stable state actually changed
            if current_state != stable_state:
                stable_state = current_state

                if stable_state == 1:
                    print("Button pressed")
                    # Output:
                    # Button pressed
                else:
                    print("Button released")
                    # Output:
                    # Button released

    # Keep loop responsive without busy-waiting
    time.sleep_ms(1)