"""Bootstrap pip from an uploaded wheel when Debian's ensurepip is unavailable."""
from pathlib import Path
import sys

wheel = next(Path("cloud-wheelhouse").glob("pip-*.whl"))
sys.path.insert(0, str(wheel.resolve()))
from pip._internal.cli.main import main

if __name__ == "__main__":
    raise SystemExit(main(["install", "--no-index", "--find-links=cloud-wheelhouse", "pip"]))
