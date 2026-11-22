"""Launch a desktop/cloud entry point from the task-organized submission."""
import os
from pathlib import Path
import runpy
import sys


def main():
    root = Path(__file__).resolve().parent
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python run.py task2/SCRIPT.py [arguments...] (see README.md)")
    entry = (root / sys.argv[1]).resolve()
    if not entry.is_relative_to(root) or not entry.is_file() or entry.suffix != ".py":
        raise SystemExit("Choose an existing Python entry point inside this submission")
    if "esp32" in entry.relative_to(root).parts:
        raise SystemExit("Upload ESP32 files to MicroPython; do not run them with desktop Python")
    paths = [root / name for name in
             ("shared", "task1", "task2", "task3/desktop", "task4", "task5", "tools", "tests")]
    sys.path[:0] = [str(entry.parent), *(str(path) for path in paths)]
    os.environ["LAB6_ROOT"] = str(root)
    os.chdir(root)
    sys.argv = [str(entry), *sys.argv[2:]]
    runpy.run_path(str(entry), run_name="__main__")


if __name__ == "__main__":
    main()
