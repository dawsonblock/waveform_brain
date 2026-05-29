#!/usr/bin/env python3
"""Board smoke check: read build ID scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from checks import read_build_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Read build ID (scaffold).")
    parser.add_argument("--device", default="", help="Board device identifier.")
    parser.add_argument("--out", default="reports/board_read_build_id.json")
    args = parser.parse_args()

    result = read_build_id(args.device or None)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print("pass" if result["pass"] else "blocked")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
