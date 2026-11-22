"""Record real ESP32-initiated HTTP storage/prediction demonstrations."""
import argparse
from datetime import datetime, timezone
from har_client import SmartwatchClient
from har_common import LABELS, append_jsonl


def main(host, stage):
    command = "store_HAR" if stage == "storage" else "classify_HAR"
    result = SmartwatchClient(host).send_command(command)
    if not result.get("id") or (stage == "prediction" and result.get("label") not in LABELS):
        raise ValueError("Device did not acknowledge a valid cloud result")
    record = {"at": datetime.now(timezone.utc).isoformat(), "stage": stage,
              "ok": True, "esp32_host": host, "command": command, "result": result,
              "transport": "ESP32 initiates HTTP directly to Flask on GCP",
              "ground_truth": None}
    append_jsonl("results/esp32_cloud_demo.jsonl", record)
    print(record)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("--stage", choices=("storage", "prediction"), required=True)
    args = parser.parse_args()
    main(args.host, args.stage)
