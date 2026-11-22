"""Verify cached probe features against a fresh official encoder call."""
import torch
from har_common import write_json
from har_dataset import UCIHARSignals
from har_normwear import make_encoder, pooled_embedding


def main():
    dataset = UCIHARSignals("data/UCI HAR Dataset", "test")
    encoder = make_encoder("vendor", "weights/normwear_pretrain_ckpt.pth")
    assert all(not parameter.requires_grad for parameter in encoder.parameters())
    saved = torch.load("artifacts/embeddings.pt", map_location="cpu", weights_only=True)
    fresh = pooled_embedding(encoder, dataset.x[:1, :3].contiguous()).cpu()
    expected = saved["test_x"][:1]
    maximum_error = float((fresh - expected).abs().max())
    matches = torch.allclose(fresh, expected, atol=1e-4, rtol=1e-4)
    assert matches
    result = {"test_index": 0, "input_shape": [1, 3, 128], "sampling_rate": 50,
              "fresh_get_embedding_matches_saved_test_feature": matches,
              "max_absolute_difference": maximum_error, "atol": 1e-4, "rtol": 1e-4,
              "all_encoder_parameters_frozen": True}
    write_json("results/encoder_cache_audit.json", result)
    print(result)


if __name__ == "__main__":
    main()
