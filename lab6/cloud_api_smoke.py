"""Exercise the deployed Flask API with a clearly identified benchmark replay."""
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error
import time
from har_common import LABELS, write_json
from har_dataset import UCIHARSignals


def request(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    call = urllib.request.Request("http://127.0.0.1:5000" + path, data=data,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(call, timeout=60) as response:
        return response.status, json.load(response)


def main():
    for attempt in range(30):
        try:
            _, health = request("/")
            break
        except urllib.error.URLError:
            if attempt == 29:
                raise
            time.sleep(1)
    x, _, label = UCIHARSignals("data/UCI HAR Dataset", "test")[0]
    payload = {"data": x[:3].tolist(), "sampling_rate": 50, "units": "g",
               "device": "UCI benchmark replay", "location": "waist",
               "setting": "Cloud API engineering check; not a live ESP32 capture",
               "label": label}
    status, stored = request("/samples", payload)
    records = [json.loads(line) for line in Path("results/cloud_samples.jsonl").read_text().splitlines()]
    assert status == 201 and any(row["id"] == stored["id"] for row in records)
    result = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "source": "UCI benchmark replay; not live hardware", "health": health,
              "storage_response": stored, "stored_on_disk": True}
    if health["prediction_ready"]:
        status, prediction = request("/predict", payload)
        assert status == 200 and len(prediction["probabilities"]) == 6
        offline = json.loads(Path("results/linear_probe.json").read_text())
        expected = LABELS[offline["predictions"][0]]
        assert prediction["label"] == expected
        result["prediction"] = prediction
        result["matches_offline_test_window_prediction"] = True
    path = Path("results/cloud_api_smoke.json")
    if path.is_file():
        previous = json.loads(path.read_text())
        history = previous.pop("previous_checks", [])
        result["previous_checks"] = history + [previous]
    write_json(path, result)
    print(result)


if __name__ == "__main__":
    main()
