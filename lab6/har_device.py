"""MicroPython ADXL345 sampling and HAR commands layered on the Lab 5 watch."""
from machine import Pin, SPI
import time
import urequests
import ujson as json
import uasyncio as asyncio
import lab5_watch

# Match lab4 checkpoint 1 and lab5 OLED/button wiring.
SPI_SCK_PIN = 5
SPI_MOSI_PIN = 19
SPI_MISO_PIN = 21
SPI_CS_PIN = 27
SAMPLE_COUNT = 128
PERIOD_US = 20000
G_PER_LSB = 0.0039  # ADXL345 full-resolution sensitivity, g/count.
SENSOR_LOCATION = "wrist"  # Actual attachment location for this experiment.
LABELS = ("WALKING", "WALKING_UPSTAIRS", "WALKING_DOWNSTAIRS",
          "SITTING", "STANDING", "LAYING")


class Accelerometer:
    def __init__(self):
        self.spi = SPI(1, baudrate=5000000, polarity=1, phase=1,
                       sck=Pin(SPI_SCK_PIN), mosi=Pin(SPI_MOSI_PIN),
                       miso=Pin(SPI_MISO_PIN))
        self.cs = Pin(SPI_CS_PIN, Pin.OUT, value=1)
        device_id = self.read(0x00, 1)[0]
        print("ADXL345 Device ID: 0x%02X" % device_id)
        if device_id != 0xE5:
            raise RuntimeError("ADXL345 not detected; check Lab 4 SPI wiring")
        self.write(0x2D, 0x00)  # Standby during configuration.
        self.write(0x31, 0x0B)  # Full resolution, +/-16 g; retain gravity.
        self.write(0x2C, 0x09)  # 50 Hz sensor output rate.
        self.write(0x2D, 0x08)  # Measurement mode.
        time.sleep_ms(100)

    def write(self, register, value):
        self.cs.value(0)
        try:
            self.spi.write(bytes((register, value)))
        finally:
            self.cs.value(1)

    def read(self, register, count):
        self.cs.value(0)
        try:
            self.spi.write(bytes((register | 0x80 | (0x40 if count > 1 else 0),)))
            return self.spi.read(count)
        finally:
            self.cs.value(1)

    def capture(self):
        data = [[], [], []]
        timestamps = []
        deadline = time.ticks_us()
        start = deadline
        for _ in range(SAMPLE_COUNT):
            remaining = time.ticks_diff(deadline, time.ticks_us())
            if remaining > 0:
                time.sleep_us(remaining)
            stamp = time.ticks_us()
            if time.ticks_diff(stamp, deadline) >= PERIOD_US:
                raise RuntimeError("Sampling deadline missed; retry capture")
            raw = self.read(0x32, 6)
            for axis in range(3):
                value = raw[2 * axis] | (raw[2 * axis + 1] << 8)
                if value & 0x8000:
                    value -= 65536
                data[axis].append(round(value * G_PER_LSB, 5))
            timestamps.append(time.ticks_diff(stamp, start))
            deadline = time.ticks_add(deadline, PERIOD_US)
        return {"data": data, "sampling_rate": 50, "units": "g",
                "device": "ESP32 + ADXL345", "timestamps_us": timestamps,
                "location": SENSOR_LOCATION, "setting": "real-world lab capture"}


class HARWatch(lab5_watch.Smartwatch):
    def __init__(self, cloud_url=""):
        super().__init__()
        self.accelerometer = Accelerometer()
        self.cloud_url = cloud_url.rstrip("/")
        self.lines = ("Lab 6 ready", "HAR via desktop", "or button A")
        self.handlers.update({"capture_HAR": (self.capture_HAR, 0),
                              "classify_HAR": (self.classify_HAR, 0),
                              "store_HAR": (self.store_HAR, 0)})

    def capture_HAR(self):
        self.display_text("Capturing HAR...")
        self.update()
        result = self.accelerometer.capture()
        self.display_text("Capture complete")
        return result

    def post_window(self, route):
        if not self.cloud_url:
            raise ValueError("Set CLOUD_URL in the checkpoint firmware first")
        payload = self.capture_HAR()
        response = None
        try:
            self.display_text("Contacting cloud")
            self.update()
            response = urequests.post(self.cloud_url + route,
                                      data=json.dumps(payload),
                                      headers={"Content-Type": "application/json"},
                                      timeout=120)
            if response.status_code not in (200, 201):
                raise RuntimeError("Cloud HTTP %s: %s" %
                                   (response.status_code, response.text[:160]))
            result = response.json()
            print("Cloud response:", result)
            return result
        finally:
            if response is not None:
                response.close()

    def store_HAR(self):
        result = self.post_window("/samples")
        self.display_text("Stored HAR " + str(result["id"])[:16])
        return result

    def classify_HAR(self):
        result = self.post_window("/predict")
        label = result.get("label")
        if label not in LABELS:
            raise ValueError("Cloud returned an invalid label")
        self.display_text(label.replace("_", " "))
        return result


async def main(cloud_url="", button_command="capture_HAR"):
    watch = HARWatch(cloud_url)
    server = None
    try:
        watch.update()
        await lab5_watch.connect_wifi()
        async def client_connected(reader, writer):
            await lab5_watch.handle_client(reader, writer, watch)
        server = await asyncio.start_server(client_connected, "0.0.0.0", 8080)
        print("Lab 6 JSON commands on port 8080")
        previous = 1
        changed = time.ticks_ms()
        stable = 1
        while True:
            raw = watch.buttons[0].value()
            if raw != previous:
                previous = raw
                changed = time.ticks_ms()
            if raw != stable and time.ticks_diff(time.ticks_ms(), changed) >= 50:
                stable = raw
                if stable == 0:
                    try:
                        print(watch.execute({"name": button_command, "args": []}))
                    except Exception as error:
                        print("HAR error:", error)
                        watch.display_text("HAR error. Check serial log.")
            watch.update()
            await asyncio.sleep_ms(10)
    finally:
        watch.stop_alarm()
        if server is not None:
            server.close()
            await server.wait_closed()
