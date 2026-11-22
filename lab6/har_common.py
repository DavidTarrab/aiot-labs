"""Shared labels, wire format, prompts, and experiment output helpers."""
import json
import math
from pathlib import Path

LABELS = ("WALKING", "WALKING_UPSTAIRS", "WALKING_DOWNSTAIRS",
          "SITTING", "STANDING", "LAYING")
CHANNELS = ("acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z")
SAMPLE_RATE = 50
WINDOW_LENGTH = 128


def validate_window(payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    data = payload.get("data")
    if payload.get("sampling_rate") != 50 or payload.get("units") != "g":
        raise ValueError("Accelerometer windows must use sampling_rate=50 and units=g")
    if not isinstance(data, list) or len(data) != 3:
        raise ValueError("data must be channels-first [3, 128]")
    for channel in data:
        if not isinstance(channel, list) or len(channel) != 128:
            raise ValueError("Each channel must contain 128 samples")
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 16
               for v in channel):
            raise ValueError("Samples must be finite numbers within +/-16 g")
    if payload.get("label") is not None and payload["label"] not in LABELS:
        raise ValueError("Unknown ground-truth label")
    return payload


def build_prompt(data, style="direct", device="Samsung Galaxy S II smartphone",
                 location="waist", setting="UCI HAR benchmark"):
    if style not in ("cot", "direct"):
        raise ValueError("style must be cot or direct")
    if hasattr(data, "tolist"):
        data = data.tolist()
    if len(data) not in (3, 6) or any(len(c) != 128 for c in data):
        raise ValueError("Expected [3 or 6, 128] raw channels")
    lines = ["You are classifying human activity from wearable IMU signals.",
             "Device: " + device, "Attached Location: " + location,
             "Setting: " + setting, "Candidate Activities: " + ", ".join(LABELS),
             "Sampling rate: 50 Hz; 128 samples; window duration: 2.56 seconds.",
             "Accelerometer units: g, total acceleration including gravity.",
             "Gyroscope units: rad/s." if len(data) == 6 else
             "Gyroscope: unavailable (not measured; no synthetic gyro channels).",
             "Channel arrays follow in chronological order:"]
    lines.extend(name + ": " + json.dumps([round(float(v), 5) for v in channel])
                 for name, channel in zip(CHANNELS, data))
    lines.append("Question: Which activity is being performed?")
    if style == "cot":
        lines.append("Explain your reasoning step by step, then give the activity. "
                     "End with LABEL: followed by exactly one candidate label.")
    else:
        lines.append("Give only the activity label, exactly as listed above.")
    return "\n".join(lines)


def parse_label(text):
    # Never search the whole explanation: it may mention several alternatives.
    last = text.strip().splitlines()[-1] if text.strip() else ""
    if last.upper().startswith("LABEL:"):
        last = last.split(":", 1)[1]
    label = last.strip().strip("`* .\"").upper().replace(" ", "_")
    if label not in LABELS:
        raise ValueError("Response did not end with a valid activity label")
    return label


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def append_jsonl(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        stream.write(json.dumps(record, allow_nan=False) + "\n")
