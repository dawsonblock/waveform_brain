#!/usr/bin/env python3
"""
Waveform Brain v1.0 — Vivado Report Package Builder

Packages all implementation sign-off reports that exist. It fails if required
implementation gate reports are missing.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile


REQUIRED = [
    "reports/cdc_critical_summary.json",
    "reports/cdc_cell_match_summary.md",
    "reports/timing_summary.rpt",
    "reports/drc.rpt",
    "reports/implementation_gate_summary.json",
    "reports/implementation_gate_summary.md",
]

OPTIONAL = [
    "reports/cdc_full.rpt",
    "reports/cdc_critical.rpt",
    "reports/cdc_full_summary.json",
    "reports/clock_interaction.rpt",
    "reports/utilization.rpt",
    "reports/preboard_local_summary.json",
    "reports/preboard_local_summary.md",
    "docs/PHASE1_SIGNOFF_SHEET.md",
    "docs/BOARD_READY_TEMPLATE.md",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Package Vivado sign-off reports.")
    parser.add_argument("--out", type=Path, default=Path("reports/vivado_signoff_package.zip"))
    args = parser.parse_args()

    missing = [Path(p) for p in REQUIRED if not Path(p).exists()]
    if missing:
        print("Missing required files:")
        for p in missing:
            print(f"  {p}")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in REQUIRED + OPTIONAL:
            p = Path(rel)
            if p.exists():
                z.write(p, rel)

    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
