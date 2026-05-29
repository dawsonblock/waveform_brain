#!/usr/bin/env python3
"""
Create a CDC sign-off archive from Vivado reports.

This does not certify the design. It only collects required artifacts into one
zip so a reviewer can inspect the CDC gate outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile


REQUIRED = [
    "reports/cdc_full.rpt",
    "reports/cdc_critical.rpt",
    "reports/clock_interaction.rpt",
    "reports/cdc_full_summary.json",
    "reports/cdc_critical_summary.json",
    "reports/cdc_cell_match_summary.md",
    "docs/PHASE1_SIGNOFF_SHEET.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Package CDC sign-off artifacts.")
    parser.add_argument("--out", type=Path, default=Path("reports/cdc_signoff_package.zip"))
    args = parser.parse_args()

    missing = [Path(p) for p in REQUIRED if not Path(p).exists()]
    if missing:
        print("Missing required files:")
        for p in missing:
            print(f"  {p}")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in REQUIRED:
            z.write(rel, rel)

    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
