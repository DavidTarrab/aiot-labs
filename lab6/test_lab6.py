"""Offline checks use synthetic fixtures, never report them as experimental results."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
from har_common import LABELS, build_prompt, parse_label, validate_window
from har_dataset import CHANNEL_SETS, UCIHARSignals
from har_normwear import pooled_embedding
from task5_linear_probe import few_shot_indices, fit_probe, load_test_embeddings
from lab6_dt2811_ms7635_rnb2135_server import create_app


def window():
    return {"data": [[0.0] * 128, [0.0] * 128, [1.0] * 128],
            "sampling_rate": 50, "units": "g"}


class Lab6Tests(unittest.TestCase):
    def test_dataset_axes_labels_and_splits(self):
        with tempfile.TemporaryDirectory() as temp:
            for split in ("train", "test"):
                base = Path(temp) / split
                (base / "Inertial Signals").mkdir(parents=True)
                for channel, template in enumerate(CHANNEL_SETS):
                    values = np.array([[channel + i / 1000 for i in range(128)]] * 6)
                    np.savetxt(base / "Inertial Signals" / template.format(split=split), values)
                np.savetxt(base / ("y_" + split + ".txt"), np.arange(1, 7), fmt="%d")
                data = UCIHARSignals(temp, split)
                self.assertEqual(tuple(data.x.shape), (6, 6, 128))
                self.assertEqual(data[5][1:], (5, "LAYING"))
                self.assertAlmostEqual(float(data.x[0, 4, 100]), 4.1, places=5)
            with self.assertRaises(ValueError):
                UCIHARSignals(temp, "validation")

    def test_payload_rejects_bad_shape_nonfinite_and_fake_units(self):
        validate_window(window())
        for key, bad in (("data", [[0] * 128] * 6), ("data", [[0] * 127] * 3),
                         ("sampling_rate", 100), ("units", "m/s2"), ("label", "RUNNING")):
            value = window()
            value[key] = bad
            with self.assertRaises(ValueError):
                validate_window(value)
        for bad in (True, float("nan"), float("inf"), 17):
            value = window()
            value["data"][0][0] = bad
            with self.assertRaises(ValueError):
                validate_window(value)

    def test_prompt_pair_and_strict_label_parsing(self):
        cot = build_prompt(window()["data"], "cot")
        direct = build_prompt(window()["data"], "direct")
        self.assertEqual(cot.rsplit("\n", 1)[0], direct.rsplit("\n", 1)[0])
        self.assertIn("Gyroscope: unavailable", direct)
        self.assertEqual(parse_label("Could be SITTING or STANDING.\nLABEL: WALKING"), "WALKING")
        with self.assertRaises(ValueError):
            parse_label("Could be SITTING or STANDING")

    def test_server_persistence_restart_and_prediction(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "captures.jsonl"
            calls = []
            def predictor(payload):
                calls.append(payload)
                return {"label": "STANDING", "class_index": 4}
            client = create_app(path, predictor).test_client()
            stored = client.post("/samples", json=window())
            self.assertEqual(stored.status_code, 201)
            predicted = client.post("/predict", json=window())
            self.assertEqual(predicted.json["label"], "STANDING")
            self.assertEqual(len(calls), 1)
            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(records), 2)
            self.assertEqual(records[1]["prediction"]["label"], "STANDING")
            self.assertEqual(records[0]["id"], stored.json["id"])
            restarted = create_app(path).test_client()
            self.assertEqual(restarted.post("/samples", json=window()).status_code, 201)
            self.assertEqual(len(path.read_text().splitlines()), 3)
            self.assertEqual(restarted.post("/predict", json=window()).status_code, 503)

    def test_server_rejects_bad_requests_without_persistence(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "captures.jsonl"
            client = create_app(path).test_client()
            self.assertEqual(client.post("/samples", json={}).status_code, 400)
            self.assertEqual(client.post("/samples", data="{", content_type="application/json").status_code, 400)
            self.assertEqual(client.post("/samples", data="a" * 40000).status_code, 413)
            self.assertFalse(path.exists())

    def test_embedding_pooling_and_sampling_contract(self):
        class Encoder:
            def get_embedding(self, x, sampling_rate, device):
                self.rate = sampling_rate
                return torch.arange(2 * 3 * 4 * 768).float().reshape(2, 3, 4, 768)
        encoder = Encoder()
        actual = pooled_embedding(encoder, torch.zeros(2, 3, 128))
        expected = torch.arange(2 * 3 * 4 * 768).float().reshape(2, 3, 4, 768).mean((1, 2))
        self.assertTrue(torch.equal(actual, expected))
        self.assertEqual(encoder.rate, 50)

    def test_few_shot_selection_and_single_linear_training(self):
        labels = torch.arange(6).repeat_interleave(20)
        indices = few_shot_indices(labels, 5, 42)
        self.assertEqual(indices, few_shot_indices(labels, 5, 42))
        self.assertEqual(torch.bincount(labels[indices]).tolist(), [5] * 6)
        features = torch.nn.functional.one_hot(labels, 6).float()
        head, mean, scale, predictions, accuracy, losses = fit_probe(
            features[indices], labels[indices], features, labels, epochs=1000)
        self.assertIsInstance(head, torch.nn.Linear)
        self.assertEqual(accuracy, 1.0)
        self.assertLess(losses[-1], losses[0])
        self.assertTrue(torch.all(scale > 0))

    def test_cached_embeddings_require_matching_encoder_and_test_order(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "embeddings.pt"
            labels = torch.arange(6)
            features = torch.randn(6, 768)
            torch.save({"features": features, "labels": labels, "encoder_sha256": "abc",
                        "channels": 3, "sampling_rate": 50, "window_length": 128,
                        "pooling": "mean_channels_patches", "split": "test"}, path)
            actual, actual_y = load_test_embeddings(path, labels, "abc")
            self.assertTrue(torch.equal(actual, features))
            self.assertTrue(torch.equal(actual_y, labels))
            with self.assertRaises(ValueError):
                load_test_embeddings(path, labels.flip(0), "abc")
            with self.assertRaises(ValueError):
                load_test_embeddings(path, labels, "other weights")


if __name__ == "__main__":
    unittest.main(verbosity=2)
