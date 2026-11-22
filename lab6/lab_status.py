"""Evidence needed before a package can be called a completed submission."""
import json
from pathlib import Path
from har_common import LABELS


def load(path, default=None):
    return json.loads(path.read_text()) if path.is_file() else default


def lines(path):
    return [json.loads(row) for row in path.read_text().splitlines() if row.strip()] if path.is_file() else []


def completed_hardware(root):
    return [row for row in lines(Path(root) / "results/esp32_llm.jsonl")
            if row.get("truth") in LABELS and row.get("label") in LABELS
            and row.get("oled_response") and not row.get("error")
            and not row.get("excluded_from_report")]


def pending_evidence(root):
    results = Path(root) / "results"
    llm = load(results / "llm_uci.json", {})
    hardware = completed_hardware(root)
    zero = load(results / "normwear_zero_shot.json", {})
    probe = load(results / "linear_probe.json", {})
    demos = lines(results / "esp32_cloud_demo.jsonl")
    pending = []
    if llm.get("completed") != 10 or llm.get("cot_errors", 1) or llm.get("direct_errors", 1):
        pending.append("complete paired LLM evaluation")
    if len(hardware) < 10 or set(row["truth"] for row in hardware) != set(LABELS):
        pending.append("10 labeled ESP32 activity captures covering all six classes")
    if zero.get("count") != 2947:
        pending.append("full-test NormWear zero-shot run")
    if probe.get("test_count") != 2947:
        pending.append("few-shot probe training/evaluation")
    elif not (Path(root) / "artifacts/linear_probe.pt").is_file():
        pending.append("saved trained linear probe")
    if not any(row.get("stage") == "storage" and row.get("ok") for row in demos):
        pending.append("ESP32-to-VM persistent storage demonstration")
    if not any(row.get("stage") == "prediction" and row.get("ok") for row in demos):
        pending.append("cloud-to-ESP32 prediction demonstration")
    return pending
