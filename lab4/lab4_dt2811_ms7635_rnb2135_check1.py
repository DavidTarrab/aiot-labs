from machine import Pin, SPI, I2C
import time
import ssd1306


# =========================================================
# OLED SETUP
# =========================================================

i2c = I2C(
    0,
    sda=Pin(22),
    scl=Pin(20),
    freq=400000
)

display = ssd1306.SSD1306_I2C(128, 32, i2c)


# =========================================================
# ADXL345 SPI SETUP
# Pins from the Lab 4 starter code
# =========================================================

spi = SPI(
    1,
    baudrate=5000000,
    polarity=1,
    phase=1,
    sck=Pin(5),
    mosi=Pin(19),
    miso=Pin(21)
)

cs = Pin(27, Pin.OUT)
cs.value(1)


# =========================================================
# ADXL345 REGISTERS
# =========================================================

DEVID = 0x00
BW_RATE = 0x2C
POWER_CTL = 0x2D
DATA_FORMAT = 0x31
DATAX0 = 0x32

SPI_READ = 1 << 7
SPI_MULTI_BYTE = 1 << 6


# =========================================================
# SPI FUNCTIONS
# =========================================================

def write_register(register, value):

    cs.value(0)

    spi.write(
        bytearray([
            register,
            value
        ])
    )

    cs.value(1)


def read_register(register, num_bytes=1):

    command = register | SPI_READ

    if num_bytes > 1:
        command |= SPI_MULTI_BYTE

    cs.value(0)

    spi.write(
        bytearray([command])
    )

    data = bytearray(num_bytes)

    spi.readinto(data)

    cs.value(1)

    return data


# =========================================================
# CONVERT TO SIGNED 16-BIT VALUE
# =========================================================

def signed_16(low, high):

    value = low | (high << 8)

    if value & 0x8000:
        value -= 65536

    return value


# =========================================================
# READ X, Y, Z
# =========================================================

def read_acceleration():

    # Read registers 0x32 through 0x37
    data = read_register(DATAX0, 6)

    x = signed_16(
        data[0],
        data[1]
    )

    y = signed_16(
        data[2],
        data[3]
    )

    z = signed_16(
        data[4],
        data[5]
    )

    return x, y, z


# =========================================================
# INITIALIZE ADXL345
# =========================================================

def setup_accelerometer():

    device_id = read_register(DEVID)[0]

    print(
        "Device ID: 0x{:02X}".format(
            device_id
        )
    )

    if device_id == 0xE5:

        print(
            "ADXL345 detected successfully!"
        )

    else:

        print(
            "ADXL345 NOT detected."
        )

        print(
            "Check wiring and SPI pins."
        )

    # 100 Hz output rate
    write_register(
        BW_RATE,
        0x0A
    )

    # Full resolution
    # +/- 2g
    # 4-wire SPI
    write_register(
        DATA_FORMAT,
        0x08
    )

    # Measurement mode
    write_register(
        POWER_CTL,
        0x08
    )


# =========================================================
# SCROLLING SETTINGS
# =========================================================

TILT_THRESHOLD = 80
SCROLL_SPEED = 2

scroll_x = 0
scroll_y = 0

text = "LAB 4 PART 1"


# =========================================================
# DETERMINE TILT DIRECTION
# =========================================================

def get_direction(x, y):

    # Board is mostly flat
    if (
        abs(x) < TILT_THRESHOLD
        and
        abs(y) < TILT_THRESHOLD
    ):

        return 0, 0


    # Left / Right
    if abs(x) >= abs(y):

        if x > TILT_THRESHOLD:

            return SCROLL_SPEED, 0

        elif x < -TILT_THRESHOLD:

            return -SCROLL_SPEED, 0


    # Up / Down
    else:

        if y > TILT_THRESHOLD:

            return 0, SCROLL_SPEED

        elif y < -TILT_THRESHOLD:

            return 0, -SCROLL_SPEED


    return 0, 0


# =========================================================
# DRAW TEXT WITH WRAPAROUND
# =========================================================

def draw_text():

    display.fill(0)

    # Draw multiple copies so text wraps around
    # when it leaves the screen.

    for x_wrap in (
        -128,
        0,
        128
    ):

        for y_wrap in (
            -32,
            0,
            32
        ):

            display.text(
                text,
                scroll_x + x_wrap,
                12 + scroll_y + y_wrap
            )

    display.show()


# =========================================================
# SETUP
# =========================================================

setup_accelerometer()

time.sleep_ms(100)


# =========================================================
# MAIN LOOP
# =========================================================

while True:

    # -------------------------
    # TASK 1
    # Read X, Y, Z
    # -------------------------

    x, y, z = read_acceleration()

    print(
        "X: {:6d}   Y: {:6d}   Z: {:6d}".format(
            x,
            y,
            z
        )
    )


    # -------------------------
    # TASK 2
    # Scroll based on tilt
    # -------------------------

    dx, dy = get_direction(
        x,
        y
    )

    scroll_x += dx
    scroll_y += dy


    # Wrap scrolling coordinates
    if scroll_x >= 128:
        scroll_x -= 128

    if scroll_x <= -128:
        scroll_x += 128

    if scroll_y >= 32:
        scroll_y -= 32

    if scroll_y <= -32:
        scroll_y += 32


    draw_text()

    time.sleep_ms(50)