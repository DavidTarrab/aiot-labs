from machine import Pin, PWM, ADC
import time

# -----------------------------
# Pin configuration
# -----------------------------

LED_PIN = 15
PIEZO_PIN = 32
LIGHT_SENSOR_PIN = 26
BUTTON_PIN = 33

DEBOUNCE_MS = 50
SAMPLE_PERIOD_MS = 100     # 100 ms = 10 Hz

# -----------------------------
# Light sensor calibration
# -----------------------------

ADC_MIN = 3500
ADC_MAX = 15000

# -----------------------------
# PWM setup
# -----------------------------

led_pwm = PWM(Pin(LED_PIN), freq=1000)
piezo_pwm = PWM(Pin(PIEZO_PIN), freq=440)

# Start outputs OFF
led_pwm.duty_u16(0)
piezo_pwm.duty_u16(0)

# -----------------------------
# ADC setup
# -----------------------------

light_sensor = ADC(Pin(LIGHT_SENSOR_PIN))
light_sensor.atten(ADC.ATTN_11DB)

# -----------------------------
# Button setup
# -----------------------------

# Active-high button:
# released -> 0
# pressed  -> 1
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)

# Last confirmed button state
stable_state = button.value()

# Information updated by interrupt
candidate_state = stable_state
last_irq_time = 0
debounce_pending = False

# Whether light/LED/piezo system is running
system_active = False


# -----------------------------
# Button interrupt
# -----------------------------

def button_irq(pin):
    global candidate_state
    global last_irq_time
    global debounce_pending

    # Record newest state
    candidate_state = pin.value()

    # Restart debounce timer
    last_irq_time = time.ticks_ms()

    debounce_pending = True


# Interrupt on both press and release
button.irq(
    trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
    handler=button_irq
)


# -----------------------------
# Output helper functions
# -----------------------------

def set_led_brightness(brightness):
    brightness = max(0.0, min(1.0, brightness))

    duty = int(brightness * 65535)

    led_pwm.duty_u16(duty)


def set_piezo(pitch, volume=0.5):
    volume = max(0.0, min(1.0, volume))

    piezo_pwm.freq(int(pitch))

    duty = int(volume * 65535)

    piezo_pwm.duty_u16(duty)


def turn_system_off():
    led_pwm.duty_u16(0)
    piezo_pwm.duty_u16(0)


# -----------------------------
# Main loop
# -----------------------------

last_sample_time = time.ticks_ms()

while True:

    # =========================================================
    # Handle software debouncing
    # =========================================================

    if debounce_pending:

        elapsed = time.ticks_diff(
            time.ticks_ms(),
            last_irq_time
        )

        # Wait until the pin has gone 50 ms without another edge
        if elapsed >= DEBOUNCE_MS:

            debounce_pending = False

            # Check actual state after debounce period
            current_state = button.value()

            # Only act if stable state really changed
            if current_state != stable_state:

                stable_state = current_state

                # Button pressed
                if stable_state == 1:

                    system_active = True

                    # Start sampling immediately
                    last_sample_time = time.ticks_ms() - SAMPLE_PERIOD_MS

                    print("Button pressed - system ON")
                    # Output:
                    # Button pressed - system ON

                # Button released
                else:

                    system_active = False

                    # Immediately turn off LED and piezo
                    turn_system_off()

                    print("Button released - system OFF")
                    # Output:
                    # Button released - system OFF

    # =========================================================
    # Run light sensor system only while button is held
    # =========================================================

    if system_active:

        current_time = time.ticks_ms()

        # Sample at 10 Hz
        if time.ticks_diff(
            current_time,
            last_sample_time
        ) >= SAMPLE_PERIOD_MS:

            last_sample_time = current_time

            # -----------------------------------------
            # Read light sensor
            # -----------------------------------------

            raw = light_sensor.read_u16()

            # Normalize according to calibrated range
            light_level = (
                (raw - ADC_MIN)
                / (ADC_MAX - ADC_MIN)
            )

            # Clamp to 0.0 - 1.0
            light_level = max(
                0.0,
                min(1.0, light_level)
            )

            # -----------------------------------------
            # LED brightness
            # -----------------------------------------

            set_led_brightness(light_level)

            # -----------------------------------------
            # Piezo pitch
            # -----------------------------------------

            # Map:
            # 0.0 -> 200 Hz
            # 1.0 -> 2000 Hz
            pitch = 200 + light_level * 1800

            set_piezo(pitch, 0.5)

            print(
                "ADC:", raw,
                "Light:", light_level,
                "Pitch:", int(pitch)
            )
            # Output example:
            # ADC: 9250 Light: 0.5 Pitch: 1100

    # Keep the main loop responsive
    time.sleep_ms(1)