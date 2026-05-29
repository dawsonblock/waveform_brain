#!/usr/bin/env python3
"""Board smoke check: PRBS capture scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from checks import prbs_capture_smoke


def main() -> int:
    parser = argparse.ArgumentParser(description="PRBS capture smoke (scaffold).")
    parser.add_argument("--device", default="", help="Board device identifier.")
    parser.add_argument("--out", default="reports/board_prbs_capture_smoke.json")
    args = parser.parse_args()

    result = prbs_capture_smoke(args.device or None)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print("pass" if result["pass"] else "blocked")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
