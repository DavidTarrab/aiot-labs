"""Task 5.1: NormWear text/signal zero-shot evaluation on the entire test split."""
import argparse
import time
from pathlib import Path
import torch
from torch.utils.data import DataLoader
from har_dataset import UCIHARSignals
from har_common import LABELS, write_json
from har_normwear import file_hash, make_zero_shot

QUESTION = "Which physical activity is the person performing?"
OPTIONS = ["The person is walking.", "The person is walking upstairs.",
           "The person is walking downstairs.", "The person is sitting.",
           "The person is standing.", "The person is lying down."]


def main(args):
    torch.manual_seed(args.seed)
    start = time.perf_counter()
    model = make_zero_shot(args.repo_parent, args.weights, args.fusion_weights, args.device)
    dataset = UCIHARSignals(args.root, "test")
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)
    predictions, truths = [], []
    pooled_features = []
    encoder_forward = model.sensor_model.get_embedding
    def capture_embedding(*forward_args, **forward_kwargs):
        raw = encoder_forward(*forward_args, **forward_kwargs)
        pooled_features.append(raw.mean(dim=(1, 2)).detach().cpu())
        return raw
    # signal_encode still performs the official zero-shot path. Retain its frozen
    # encoder output for Task 5.2 so identical test windows need not be encoded twice.
    model.sensor_model.get_embedding = capture_embedding
    if args.device.startswith("cuda"):
        torch.cuda.synchronize()
    inference_start = time.perf_counter()
    with torch.inference_mode():
        texts = model.txt_encode([QUESTION] + OPTIONS)
        query, options = texts[:1], texts[1:]
        for x, y, _ in loader:
            # Match the deployed 3-axis ADXL345 input; no gyro or fabricated channels.
            signal = model.signal_encode(x[:, :3].to(args.device), query, sampling_rate=50)
            probabilities = model.inference(signal, options)
            predictions.extend(probabilities.argmax(dim=1).cpu().tolist())
            truths.extend(y.tolist())
            print("Evaluated", len(truths), "/", len(dataset), flush=True)
    if args.device.startswith("cuda"):
        torch.cuda.synchronize()
    inference_seconds = time.perf_counter() - inference_start
    embedding_path = Path(args.embeddings)
    embedding_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"features": torch.cat(pooled_features),
                "labels": torch.tensor(truths, dtype=torch.long),
                "encoder_sha256": file_hash(args.weights), "channels": 3,
                "sampling_rate": 50, "window_length": 128,
                "pooling": "mean_channels_patches", "split": "test"}, embedding_path)
    accuracy = sum(p == y for p, y in zip(predictions, truths)) / len(truths)
    matrix = torch.zeros((6, 6), dtype=torch.int64)
    for y, p in zip(truths, predictions):
        matrix[y, p] += 1
    write_json(args.output, {"accuracy": accuracy, "count": len(truths),
               "device": args.device, "inference_seconds": inference_seconds,
               "total_seconds": time.perf_counter() - start, "seed": args.seed,
               "shape": [len(truths), 3, 128], "sampling_rate": 50,
               "units": "g", "question": QUESTION, "options": OPTIONS,
               "labels": list(LABELS), "predictions": predictions, "truths": truths,
               "confusion_matrix": matrix.tolist(),
               "encoder_sha256": file_hash(args.weights),
               "fusion_sha256": file_hash(args.fusion_weights)})
    print("Zero-shot accuracy:", accuracy, "inference seconds:", inference_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--repo-parent", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--fusion-weights", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=4764)
    parser.add_argument("--output", default="results/normwear_zero_shot.json")
    parser.add_argument("--embeddings", default="artifacts/zero_shot_test_embeddings.pt")
    main(parser.parse_args())
