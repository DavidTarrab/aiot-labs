"""Verify persisted real-device windows and reproduce their cloud predictions."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from har_common import LABELS, validate_window, write_json
from har_normwear import Predictor


def main(demos, storage, repo_parent, weights, probe):
    demonstrations = [json.loads(row) for row in Path(demos).read_text().splitlines() if row.strip()]
    records = {r["id"]: r for r in
               (json.loads(row) for row in Path(storage).read_text().splitlines() if row.strip())}
    predictor = Predictor(repo_parent, weights, probe, device="cpu")
    verified = []
    for demo in demonstrations:
        assert demo["ok"] and demo["stage"] in ("storage", "prediction")
        identifier = demo["result"]["id"]
        stored = records[identifier]
        window = validate_window(stored["window"])
        assert window["device"] == "ESP32 + ADXL345"
        stamps = window["timestamps_us"]
        assert len(stamps) == 128 and all(b > a for a, b in zip(stamps, stamps[1:]))
        rate = 127000000 / (stamps[-1] - stamps[0])
        assert 49 < rate < 51, rate
        result = {"id": identifier, "stage": demo["stage"], "persisted": True,
                  "shape": [3, 128], "effective_sampling_rate": rate,
                  "window_sha256": hashlib.sha256(json.dumps(window, sort_keys=True).encode()).hexdigest()}
        if demo["stage"] == "prediction":
            fresh = predictor(window)
            original = stored["prediction"]
            assert fresh["label"] == original["label"] == demo["result"]["label"]
            assert fresh["class_index"] == original["class_index"]
            assert LABELS[original["class_index"]] == original["label"]
            assert abs(sum(original["probabilities"]) - 1) < 1e-5
            delta = max(abs(a - b) for a, b in zip(fresh["probabilities"], original["probabilities"]))
            assert delta < 1e-5, delta
            result.update(label=fresh["label"], reproduced_prediction=True,
                          maximum_probability_difference=delta)
        else:
            assert stored["prediction"] is None
        verified.append(result)
    assert {r["stage"] for r in verified} == {"storage", "prediction"}
    output = {"verified_at": datetime.now(timezone.utc).isoformat(), "records": verified,
              "all_persisted": True, "live_predictions_reproduced": True,
              "scope": "Real-device cloud records; visual OLED confirmation is separately recorded by the wearer."}
    write_json("results/live_cloud_verification.json", output)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demos", default="results/esp32_cloud_demo.jsonl")
    parser.add_argument("--storage", default="results/cloud_samples.jsonl")
    parser.add_argument("--repo-parent", default="vendor")
    parser.add_argument("--weights", default="weights/normwear_pretrain_ckpt.pth")
    parser.add_argument("--probe", default="artifacts/linear_probe.pt")
    args = parser.parse_args()
    main(args.demos, args.storage, args.repo_parent, args.weights, args.probe)
