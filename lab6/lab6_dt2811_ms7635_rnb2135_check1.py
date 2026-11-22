"""Checkpoint 1: paired CoT/direct evaluation on ten seeded UCI test windows."""
import argparse
import random
import time
from har_common import LABELS, write_json
from har_dataset import UCIHARSignals
from har_gemini import classify


def evaluate(root, output="results/llm_uci.json", count=10, seed=4764, channels=6):
    dataset = UCIHARSignals(root, "test")
    indices = random.Random(seed).sample(range(len(dataset)), count)
    records = []
    for number, index in enumerate(indices):
        x, y, truth = dataset[index]
        record = {"index": index, "truth": truth, "channels": channels}
        # Alternate order to reduce a systematic ordering effect.
        styles = ("cot", "direct") if number % 2 == 0 else ("direct", "cot")
        for style in styles:
            started = time.perf_counter()
            try:
                record[style] = classify(x[:channels], style)
            except Exception as error:
                record[style] = {"label": None, "error": str(error)}
            record[style]["seconds"] = time.perf_counter() - started
        records.append(record)
        summary = {"seed": seed, "count": count, "completed": len(records),
                   "channels": channels, "records": records}
        for style in ("cot", "direct"):
            summary[style + "_accuracy"] = sum(
                r[style]["label"] == r["truth"] for r in records) / len(records)
            summary[style + "_errors"] = sum(r[style]["label"] is None for r in records)
        paired = [r for r in records if r["cot"]["label"] and r["direct"]["label"]]
        summary["paired_valid"] = len(paired)
        summary["agreement"] = (sum(r["cot"]["label"] == r["direct"]["label"]
                                    for r in paired) / len(paired)) if paired else None
        write_json(output, summary)
        print(index, truth, record["cot"]["label"], record["direct"]["label"], flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--output", default="results/llm_uci.json")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=4764)
    parser.add_argument("--channels", type=int, choices=(3, 6), default=6)
    args = parser.parse_args()
    evaluate(args.root, args.output, args.count, args.seed, args.channels)
