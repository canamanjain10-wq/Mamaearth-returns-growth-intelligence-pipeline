"""Input-file and pipeline validation helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def validate_input_files() -> bool:
    """Check that the three required CSVs exist and have expected shapes."""
    print("=" * 60)
    print("VALIDATE INPUT FILES")
    print("=" * 60)

    required = {
        "customers.csv": 45,
        "products.csv": 16,
        "orders.csv": 180,
    }
    ok = True
    for fname, expected_rows in required.items():
        path = DATA_DIR / fname
        if not path.exists():
            print(f"ERROR: missing {path}")
            ok = False
            continue
        df = pd.read_csv(path)
        print(f"{fname}: {len(df)} rows (expected {expected_rows})")
        if len(df) != expected_rows:
            print(f"  → MISMATCH")
            ok = False
        else:
            print(f"  → OK")
    return ok


if __name__ == "__main__":
    if not validate_input_files():
        sys.exit(1)
    print("All input files validated.")