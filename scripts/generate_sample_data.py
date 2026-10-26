"""Regenerate deterministic local CSV demonstrations from the backend engine.

Run from the repository root: python scripts/generate_sample_data.py
These files contain synthetic demonstration data, never observed event sales.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.data_generation import get_sample_dataframe  # noqa: E402


def main() -> None:
    target = ROOT / "data"
    target.mkdir(exist_ok=True)
    names = {
        "standard": "sample_events.csv",
        "sellout": "sample_sellout_events.csv",
        "problematic": "sample_invalid_data.csv",
    }
    for dataset_id, name in names.items():
        frame = get_sample_dataframe(dataset_id)
        path = target / name
        frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
        print(f"{path.name}: {len(frame)} rows; synthetic demonstration data")


if __name__ == "__main__":
    main()
