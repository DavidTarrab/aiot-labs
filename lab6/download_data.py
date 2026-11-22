"""Download the official UCI archive, including its nested raw-signal ZIP."""
import argparse
import hashlib
import io
from pathlib import Path
import urllib.request
import zipfile
from har_common import write_json

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

URL = ("https://archive.ics.uci.edu/static/public/240/"
       "human+activity+recognition+using+smartphones.zip")


def extract_safe(archive, destination):
    destination = destination.resolve()
    for item in archive.infolist():
        target = (destination / item.filename).resolve()
        if not target.is_relative_to(destination):
            raise ValueError("Unsafe archive member")
    archive.extractall(destination)


def main(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=120) as response:
        content = response.read()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        nested = [n for n in archive.namelist() if n.endswith("UCI HAR Dataset.zip")]
        if nested:
            with zipfile.ZipFile(io.BytesIO(archive.read(nested[0]))) as inner:
                extract_safe(inner, destination)
        else:
            extract_safe(archive, destination)
    write_json(destination / "download_manifest.json",
               {"url": URL, "sha256": hashlib.sha256(content).hexdigest()})
    print("Dataset:", destination / "UCI HAR Dataset")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", default="data")
    main(parser.parse_args().destination)
