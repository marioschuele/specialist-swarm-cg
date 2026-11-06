"""
Copy the current outputs/ files into outputs/<label>/ so that the baseline run
(no firm-voice skill) and the run with the skill can be compared afterwards.
outputs/ is git-ignored by team rule - never commit it.

Usage:
    python snapshot_run.py baseline     # after the run without the skill
    python snapshot_run.py with-voice   # after the run with the skill
"""

import shutil
import sys
from pathlib import Path

OUTPUT_DIR = Path("outputs")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python snapshot_run.py <label>")
    label = sys.argv[1].strip()
    if not label.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("Label: letters, digits, - and _ only.")

    target = OUTPUT_DIR / label
    target.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in OUTPUT_DIR.iterdir():
        if f.is_file():
            shutil.copy2(f, target / f.name)
            copied += 1
    print(f"Copied {copied} file(s) to {target}/")


if __name__ == "__main__":
    main()
