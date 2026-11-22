"""Verify the real pretrained encoder on a real UCI window before a long VM run."""
import platform
import time
import torch
from har_common import write_json
from har_dataset import UCIHARSignals
from har_normwear import make_encoder, pooled_embedding


def main():
    start = time.perf_counter()
    dataset = UCIHARSignals("data/UCI HAR Dataset", "test")
    encoder = make_encoder("vendor", "weights/normwear_pretrain_ckpt.pth")
    with torch.inference_mode():
        x = dataset.x[:4, :3].contiguous()
        inference_start = time.perf_counter()
        embedding = pooled_embedding(encoder, x)
        seconds = time.perf_counter() - inference_start
        timings = []
        for threads in (2, 4):
            torch.set_num_threads(threads)
            started = time.perf_counter()
            large = pooled_embedding(encoder, dataset.x[:16, :3].contiguous())
            elapsed = time.perf_counter() - started
            timings.append({"threads": threads, "batch_size": 16, "seconds": elapsed,
                            "windows_per_second": 16 / elapsed})
            print("Throughput check:", timings[-1], flush=True)
    result = {"input_shape": list(x.shape), "embedding_shape": list(embedding.shape),
              "finite": bool(torch.isfinite(embedding).all()),
              "batch_seconds": seconds, "total_seconds": time.perf_counter() - start,
              "torch_version": torch.__version__, "python": platform.python_version(),
              "host": platform.node(), "device": "cpu", "threads": torch.get_num_threads(),
              "timings": timings,
              "recommended_threads": min(timings, key=lambda row: row["seconds"])["threads"]}
    write_json("results/cloud_encoder_smoke.json", result)
    print(result, flush=True)


if __name__ == "__main__":
    main()
