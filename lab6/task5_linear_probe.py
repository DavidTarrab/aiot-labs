"""Task 5.2: 5-10 train windows/class, frozen NormWear, and a single linear head."""
import argparse
from pathlib import Path
import time
import torch
from har_common import LABELS, write_json
from har_dataset import UCIHARSignals
from har_normwear import file_hash, make_encoder, pooled_embedding


def few_shot_indices(labels, shots=10, seed=4764):
    if not 5 <= shots <= 10:
        raise ValueError("Use 5 through 10 shots per class")
    generator = torch.Generator().manual_seed(seed)
    result = []
    for label in range(6):
        choices = (labels == label).nonzero().flatten()
        if len(choices) < shots:
            raise ValueError("Not enough examples for class " + str(label))
        result.extend(choices[torch.randperm(len(choices), generator=generator)[:shots]].tolist())
    return result


@torch.inference_mode()
def extract(encoder, dataset, indices, batch_size, device):
    features = []
    for offset in range(0, len(indices), batch_size):
        batch = indices[offset:offset + batch_size]
        x = dataset.x[batch, :3].contiguous()
        features.append(pooled_embedding(encoder, x, device).cpu())
        print("Embedded", min(offset + batch_size, len(indices)), "/", len(indices), flush=True)
    return torch.cat(features), dataset.y[indices]


def fit_probe(train_x, train_y, test_x, test_y, epochs=100, seed=4764):
    torch.manual_seed(seed)
    # Fixed transform estimated only from the few-shot training examples.
    mean = train_x.mean(dim=0)
    scale = train_x.std(dim=0, unbiased=False).clamp_min(1e-6)
    train_x = (train_x - mean) / scale
    test_x = (test_x - mean) / scale
    head = torch.nn.Linear(train_x.shape[1], 6)
    optimizer = torch.optim.AdamW(head.parameters(), lr=0.001, weight_decay=0.01)
    losses = []
    for _ in range(epochs):
        head.train()
        optimizer.zero_grad()
        loss = torch.nn.functional.cross_entropy(head(train_x), train_y)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    head.eval()
    with torch.no_grad():
        predictions = head(test_x).argmax(dim=1)
        accuracy = float((predictions == test_y).float().mean())
    return head, mean, scale, predictions, accuracy, losses


def load_test_embeddings(path, labels, encoder_sha256):
    pack = torch.load(path, map_location="cpu", weights_only=True)
    if (pack["encoder_sha256"] != encoder_sha256 or pack["channels"] != 3
            or pack["sampling_rate"] != 50 or pack["window_length"] != 128
            or pack["pooling"] != "mean_channels_patches" or pack["split"] != "test"
            or not torch.equal(pack["labels"], labels)
            or tuple(pack["features"].shape) != (len(labels), 768)
            or not torch.isfinite(pack["features"]).all()):
        raise ValueError("Cached test embeddings do not match the encoder/dataset contract")
    return pack["features"], pack["labels"]


def main(args):
    start = time.perf_counter()
    torch.manual_seed(args.seed)
    train = UCIHARSignals(args.root, "train")
    test = UCIHARSignals(args.root, "test")
    indices = few_shot_indices(train.y, args.shots, args.seed)
    encoder = make_encoder(args.repo_parent, args.weights, args.device)
    digest = file_hash(args.weights)
    train_x, train_y = extract(encoder, train, indices, args.batch_size, args.device)
    if args.test_embeddings:
        test_x, test_y = load_test_embeddings(args.test_embeddings, test.y, digest)
        print("Reused", len(test_y), "validated test embeddings from zero-shot run", flush=True)
    else:
        test_x, test_y = extract(encoder, test, list(range(len(test))), args.batch_size, args.device)
    # inference_mode tensors must be copied into normal tensors for autograd training.
    train_x, train_y = train_x.clone(), train_y.clone()
    test_x, test_y = test_x.clone(), test_y.clone()
    artifacts = Path(args.artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    torch.save({"train_x": train_x, "train_y": train_y, "test_x": test_x,
                "test_y": test_y, "train_indices": indices, "encoder_sha256": digest},
               artifacts / "embeddings.pt")
    head, mean, scale, predictions, accuracy, losses = fit_probe(
        train_x, train_y, test_x, test_y, args.epochs, args.seed)
    torch.save({"state_dict": head.state_dict(), "mean": mean, "scale": scale,
                "labels": list(LABELS), "channels": 3, "sampling_rate": 50,
                "window_length": 128, "units": "g", "pooling": "mean_channels_patches",
                "encoder_sha256": digest, "train_indices": indices}, artifacts / "linear_probe.pt")
    baseline_path = Path(args.baseline)
    import json
    baseline = json.loads(baseline_path.read_text()) if baseline_path.is_file() else None
    if baseline and (baseline["encoder_sha256"] != digest or baseline["shape"][1] != 3):
        raise ValueError("Baseline must use the same encoder and channels")
    write_json(args.output, {"accuracy": accuracy,
               "zero_shot_accuracy": baseline["accuracy"] if baseline else None,
               "improvement_percentage_points": (100 * (accuracy - baseline["accuracy"])) if baseline else None,
               "test_count": len(test), "train_count": len(indices), "shots": args.shots,
               "epochs": args.epochs, "seed": args.seed, "device": args.device,
               "test_embeddings_reused": bool(args.test_embeddings),
               "seconds": time.perf_counter() - start, "train_indices": indices,
               "losses": losses, "predictions": predictions.tolist(), "truths": test_y.tolist(),
               "encoder_sha256": digest})
    print("Linear-probe test accuracy:", accuracy)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--repo-parent", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--shots", type=int, default=10, choices=range(5, 11))
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=4764)
    parser.add_argument("--artifacts", default="artifacts")
    parser.add_argument("--baseline", default="results/normwear_zero_shot.json")
    parser.add_argument("--output", default="results/linear_probe.json")
    parser.add_argument("--test-embeddings", help="Reuse validated frozen test embeddings from Task 5.1")
    main(parser.parse_args())
