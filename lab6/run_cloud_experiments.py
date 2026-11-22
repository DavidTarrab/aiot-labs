"""Run measured cloud checks, probe training, and full-test zero-shot evaluation."""
import json
from datetime import datetime, timezone
import importlib.metadata
import os
from pathlib import Path
import platform
import subprocess
import sys
from har_common import write_json


def run(*args):
    print("RUN:", " ".join(args), flush=True)
    subprocess.run([sys.executable, "-u", *args], check=True)


def main():
    Path("results").mkdir(exist_ok=True)
    write_json("results/cloud_environment.json", {
        "started_at": datetime.now(timezone.utc).isoformat(), "host": platform.node(),
        "platform": platform.platform(), "python": platform.python_version(),
        "logical_cpus": os.cpu_count(), "project": "eecs-aiot", "zone": "us-east4-b",
        "device": "cpu", "text_model": "muzammil-eds/tinyllama-2.5T-Clinical-v2",
        "packages": {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}})
    run("-m", "unittest", "-v", "test_lab6")
    run("har_dataset.py", "data/UCI HAR Dataset")
    run("cloud_smoke.py")
    smoke = json.loads(Path("results/cloud_encoder_smoke.json").read_text())
    os.environ["NORMWEAR_NUM_THREADS"] = str(smoke["recommended_threads"])
    run("task5_zero_shot.py", "data/UCI HAR Dataset", "--repo-parent", "vendor",
        "--weights", "weights/normwear_pretrain_ckpt.pth", "--fusion-weights",
        "weights/normwear_msitf_zeroshot_last_checkpoint-5.pth", "--device", "cpu", "--batch-size", "16")
    run("task5_linear_probe.py", "data/UCI HAR Dataset", "--repo-parent", "vendor",
        "--weights", "weights/normwear_pretrain_ckpt.pth", "--device", "cpu", "--batch-size", "16",
        "--test-embeddings", "artifacts/zero_shot_test_embeddings.pt")
    zero = json.loads(Path("results/normwear_zero_shot.json").read_text())
    probe = json.loads(Path("results/linear_probe.json").read_text())
    if zero["encoder_sha256"] != probe["encoder_sha256"] or zero["truths"] != probe["truths"]:
        raise ValueError("The two evaluations do not use the same encoder/test labels")
    probe["zero_shot_accuracy"] = zero["accuracy"]
    probe["improvement_percentage_points"] = 100 * (probe["accuracy"] - zero["accuracy"])
    write_json("results/linear_probe.json", probe)
    write_json("results/cloud_comparison.json", {
        "zero_shot_accuracy": zero["accuracy"], "linear_probe_accuracy": probe["accuracy"],
        "improvement_percentage_points": probe["improvement_percentage_points"],
        "test_count": len(zero["truths"]), "device": "cpu"})
    print("CLOUD EXPERIMENTS COMPLETE", flush=True)


if __name__ == "__main__":
    main()
