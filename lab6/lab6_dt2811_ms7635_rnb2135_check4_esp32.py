"""Checkpoint 4: button A sends one window to NormWear and displays prediction."""
import uasyncio as asyncio
from har_device import main

CLOUD_URL = "http://136.82.132.175"

if __name__ == "__main__":
    asyncio.run(main(CLOUD_URL, "classify_HAR"))
