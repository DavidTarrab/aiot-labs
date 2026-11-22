"""NormWear integration: frozen encoder, torch CWT, and identical pooling at serving."""
import hashlib
import os
from pathlib import Path
import sys
import torch
from har_common import LABELS, validate_window


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configure_repo(repo_parent):
    # repo_parent contains the cloned directory named NormWear.
    root = Path(repo_parent).resolve()
    if not (root / "NormWear/main_model.py").is_file():
        raise ValueError("--repo-parent must contain NormWear/main_model.py")
    sys.path.insert(0, str(root))


def make_encoder(repo_parent, weights, device="cpu"):
    if not Path(weights).is_file():
        raise FileNotFoundError(weights)
    configure_repo(repo_parent)
    from NormWear.main_model import NormWearModel
    encoder = NormWearModel(weight_path=str(weights), optimized_cwt=True).to(device)
    encoder.eval().requires_grad_(False)
    if os.getenv("NORMWEAR_NUM_THREADS"):
        torch.set_num_threads(int(os.environ["NORMWEAR_NUM_THREADS"]))
    # Upstream calls .numpy() on its input; keep raw windows on CPU even on CUDA.
    original = encoder.get_embedding
    def embedding(x, sampling_rate=50, device=torch.device(device)):
        return original(x.detach().cpu().contiguous(), sampling_rate=sampling_rate,
                        device=device)
    encoder.get_embedding = embedding
    return encoder


@torch.inference_mode()
def pooled_embedding(encoder, x, device="cpu"):
    raw = encoder.get_embedding(x.detach().cpu().contiguous(), sampling_rate=50,
                                device=torch.device(device))
    if raw.ndim != 4 or raw.shape[-1] != 768:
        raise RuntimeError("Expected NormWear output [B,C,P,768], got " + str(raw.shape))
    result = raw.mean(dim=(1, 2))
    if not torch.isfinite(result).all():
        raise RuntimeError("Non-finite NormWear embedding")
    return result


def make_zero_shot(repo_parent, weights, fusion_weights, device="cpu"):
    configure_repo(repo_parent)
    if not Path(weights).is_file() or not Path(fusion_weights).is_file():
        raise FileNotFoundError("Both encoder and MSiTF checkpoints are required")
    from NormWear.zero_shot.msitf_fusion import NormWearZeroShot
    # Load fusion ourselves: upstream catches load errors and continues with random weights.
    text_path = os.getenv("NORMWEAR_TEXT_MODEL")
    if text_path:
        # The upstream constructor hardcodes a Hub ID. Redirect its two loading
        # calls to the identical downloaded model when the VM has no internet.
        from unittest.mock import patch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        tokenizer_loader = AutoTokenizer.from_pretrained
        text_loader = AutoModelForCausalLM.from_pretrained
        with patch.object(AutoTokenizer, "from_pretrained",
                          side_effect=lambda *a, **kw: tokenizer_loader(text_path, local_files_only=True)), \
             patch.object(AutoModelForCausalLM, "from_pretrained",
                          side_effect=lambda *a, **kw: text_loader(text_path, local_files_only=True)):
            model = NormWearZeroShot(weight_path=str(weights), msitf_ckpt="")
    else:
        model = NormWearZeroShot(weight_path=str(weights), msitf_ckpt="")
    state = torch.load(fusion_weights, map_location="cpu", weights_only=True)
    model.aggregator.load_state_dict(state, strict=True)
    model.sensor_model.optimized_cwt = True
    original = model.sensor_model.get_embedding
    def embedding(x, sampling_rate=50, device=torch.device(device)):
        return original(x.detach().cpu().contiguous(), sampling_rate=sampling_rate,
                        device=device)
    model.sensor_model.get_embedding = embedding
    model = model.to(device).eval().requires_grad_(False)
    if os.getenv("NORMWEAR_NUM_THREADS"):
        torch.set_num_threads(int(os.environ["NORMWEAR_NUM_THREADS"]))
    return model


class Predictor:
    def __init__(self, repo_parent, weights, probe_path, device="cpu"):
        self.device = device
        pack = torch.load(probe_path, map_location="cpu", weights_only=True)
        if pack["labels"] != list(LABELS) or pack["channels"] != 3:
            raise ValueError("Probe must use the six HAR labels and three accelerometer channels")
        if pack["encoder_sha256"] != file_hash(weights):
            raise ValueError("Probe and encoder checkpoint do not match")
        self.encoder = make_encoder(repo_parent, weights, device)
        self.head = torch.nn.Linear(768, 6).to(device)
        self.head.load_state_dict(pack["state_dict"])
        self.head.eval().requires_grad_(False)
        self.mean = pack["mean"].to(device)
        self.scale = pack["scale"].to(device)

    @torch.inference_mode()
    def __call__(self, payload):
        validate_window(payload)
        x = torch.tensor(payload["data"], dtype=torch.float32).unsqueeze(0)
        embedding = pooled_embedding(self.encoder, x, self.device)
        probabilities = self.head((embedding - self.mean) / self.scale).softmax(dim=1)[0]
        index = int(probabilities.argmax())
        return {"label": LABELS[index], "class_index": index,
                "probabilities": probabilities.cpu().tolist()}
