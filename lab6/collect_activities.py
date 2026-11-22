"""Guided collection of ten user-confirmed ESP32/Gemini activity windows."""
import argparse
import json
import time
from har_common import LABELS
from lab6_dt2811_ms7635_rnb2135_check2_app import classify_HAR


def main(host, location, style):
    schedule = list(LABELS) + list(LABELS[:4])
    print("Sensor placement:", location)
    print("Each capture records the activity you confirm as ground truth.")
    print("Continue the activity through the three-second countdown and 2.56-second capture.")
    print("Ctrl-C stops collection; completed records remain saved.")
    for index, activity in enumerate(schedule, 1):
        while True:
            input("\n%d/10: Perform %s. Press Enter when you are doing this activity: "
                  % (index, activity))
            for remaining in (3, 2, 1):
                print("Capturing in", remaining, flush=True)
                time.sleep(1)
            result = json.loads(classify_HAR(host, truth=activity, location=location, style=style))
            print("Prediction:", result.get("label"), "| Ground truth:", activity)
            if result.get("error"):
                print("Capture/query failed:", result["error"])
                print("The failed attempt is saved. Repeat this activity to obtain a valid result.")
                continue
            print("OLED:", result["oled_response"])
            break
    print("\nTen additional labeled captures collected. Regenerate the report to review accuracy.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--location", required=True, help="Actual attachment location, e.g. waist")
    parser.add_argument("--style", choices=("direct", "cot"), default="direct")
    args = parser.parse_args()
    try:
        main(args.host, args.location, args.style)
    except KeyboardInterrupt:
        print("\nCollection stopped; completed captures remain in results/esp32_llm.jsonl.")
