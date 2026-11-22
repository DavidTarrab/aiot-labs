"""Independently verify full-test metrics and the saved probe's reproducibility."""
from datetime import datetime, timezone
import json
from pathlib import Path
import torch
from har_common import LABELS, write_json


def main():
    zero = json.loads(Path("results/normwear_zero_shot.json").read_text())
    probe = json.loads(Path("results/linear_probe.json").read_text())
    provenance = json.loads(Path("results/normwear_setup.json").read_text())
    digest = provenance["sha256"]["normwear_pretrain_ckpt.pth"]
    assert zero["shape"] == [2947, 3, 128]
    assert zero["truths"] == probe["truths"]
    for result in (zero, probe):
        assert result["encoder_sha256"] == digest
        assert len(result["predictions"]) == len(result["truths"]) == 2947
        assert all(type(p) is int and 0 <= p < 6 for p in result["predictions"])
        accuracy = sum(p == y for p, y in zip(result["predictions"], result["truths"])) / 2947
        assert abs(result["accuracy"] - accuracy) < 1e-6
    features = torch.load("artifacts/embeddings.pt", map_location="cpu", weights_only=True)
    saved = torch.load("artifacts/linear_probe.pt", map_location="cpu", weights_only=True)
    assert saved["labels"] == list(LABELS) and saved["encoder_sha256"] == digest
    assert tuple(features["train_x"].shape) == (60, 768)
    assert tuple(features["test_x"].shape) == (2947, 768)
    assert torch.bincount(features["train_y"], minlength=6).tolist() == [10] * 6
    assert features["test_y"].tolist() == probe["truths"]
    head = torch.nn.Linear(768, 6)
    head.load_state_dict(saved["state_dict"])
    with torch.inference_mode():
        x = (features["test_x"] - saved["mean"]) / saved["scale"]
        predictions = head(x).argmax(dim=1)
    assert predictions.tolist() == probe["predictions"]
    result = {"verified_at": datetime.now(timezone.utc).isoformat(), "test_count": 2947,
              "zero_shot_accuracy": zero["accuracy"], "probe_accuracy": probe["accuracy"],
              "encoder_matches_official_download": True, "saved_probe_reproduces_all_predictions": True,
              "train_embedding_shape": [60, 768], "test_embedding_shape": [2947, 768],
              "training_examples_per_class": [10] * 6}
    write_json("results/cloud_verification.json", result)
    print(result)


if __name__ == "__main__":
    main()
