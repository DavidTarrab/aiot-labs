"""Task 1: raw UCI HAR windows, never the 561 engineered features."""
import argparse
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from har_common import LABELS

HAR_LABELS = dict(enumerate(LABELS, 1))
CHANNEL_SETS = ["total_acc_x_{split}.txt", "total_acc_y_{split}.txt",
                "total_acc_z_{split}.txt", "body_gyro_x_{split}.txt",
                "body_gyro_y_{split}.txt", "body_gyro_z_{split}.txt"]


class UCIHARSignals(Dataset):
    def __init__(self, root, split="train"):
        if split not in ("train", "test"):
            raise ValueError("split must be train or test")
        base = Path(root) / split
        arrays = [np.loadtxt(base / "Inertial Signals" / name.format(split=split),
                             dtype=np.float32, ndmin=2) for name in CHANNEL_SETS]
        x = np.stack(arrays, axis=1)
        y = np.loadtxt(base / ("y_" + split + ".txt"), dtype=np.int64, ndmin=1)
        if x.shape != (len(y), 6, 128) or not np.isfinite(x).all():
            raise ValueError("Invalid UCI signal shape or non-finite values")
        if not np.isin(y, np.arange(1, 7)).all():
            raise ValueError("UCI labels must be in 1..6")
        # Preserve physical units. No test statistics or normalization leakage.
        self.x = torch.from_numpy(x)
        self.y = torch.from_numpy(y - 1)
        self.split = split

    def __len__(self):
        return len(self.y)

    def __getitem__(self, i):
        y = int(self.y[i])
        return self.x[i], y, LABELS[y]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    args = parser.parse_args()
    for split in ("train", "test"):
        dataset = UCIHARSignals(args.root, split)
        xb, yb, names = next(iter(DataLoader(dataset, batch_size=32,
                                             shuffle=split == "train")))
        print(split, "windows:", len(dataset), "x:", xb.shape, "y:", yb.shape,
              "names:", names[:3])
