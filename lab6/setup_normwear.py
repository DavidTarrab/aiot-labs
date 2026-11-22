"""Download pinned upstream source and both official v1.0.0-alpha checkpoints."""
import argparse
import hashlib
import io
from pathlib import Path
import urllib.request
import zipfile
from har_common import write_json

REPOSITORY = "Mobile-Sensing-and-UbiComp-Laboratory/NormWear"
REVISION = "07517fcb13def8c89cb586128359cec02f86ec8d"
ASSETS = ("normwear_pretrain_ckpt.pth", "normwear_msitf_zeroshot_last_checkpoint-5.pth")


def download(url, target):
    if target.is_file():
        return
    partial = target.with_suffix(target.suffix + ".partial")
    print("Downloading", url, flush=True)
    with urllib.request.urlopen(url, timeout=180) as response, partial.open("wb") as stream:
        while chunk := response.read(1024 * 1024):
            stream.write(chunk)
    partial.replace(target)


def main(destination):
    root = Path(destination).resolve()
    vendor = root / "vendor"
    weights = root / "weights"
    vendor.mkdir(parents=True, exist_ok=True)
    weights.mkdir(parents=True, exist_ok=True)
    source = vendor / ("NormWear-" + REVISION + ".zip")
    download("https://codeload.github.com/" + REPOSITORY + "/zip/" + REVISION, source)
    repo = vendor / "NormWear"
    if not repo.exists():
        with zipfile.ZipFile(source) as archive:
            prefix = "NormWear-" + REVISION + "/"
            for name in archive.namelist():
                if not name.startswith(prefix) or name.endswith("/"):
                    continue
                target = (repo / name[len(prefix):]).resolve()
                if not target.is_relative_to(repo.resolve()):
                    raise ValueError("Unsafe source archive path")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
    checksums = {}
    for name in ASSETS:
        target = weights / name
        download("https://github.com/" + REPOSITORY + "/releases/download/v1.0.0-alpha/" + name, target)
        digest = hashlib.sha256()
        with target.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        checksums[name] = digest.hexdigest()
    write_json(root / "results/normwear_setup.json",
               {"repository": REPOSITORY, "revision": REVISION, "sha256": checksums})
    print("Ready. --repo-parent", vendor, "--weights", weights / ASSETS[0])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", default=".")
    main(parser.parse_args().destination)
