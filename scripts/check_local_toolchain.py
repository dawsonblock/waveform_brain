#!/usr/bin/env python3
"""Check local toolchain availability for source/proof/board modes."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hash_source_tree import compute_source_tree_hash  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = PROJECT_ROOT / "reports" / "local_toolchain_summary.json"
REPORT_MD = PROJECT_ROOT / "reports" / "local_toolchain_summary.md"

MODE_REQUIRED = {
    "source": {"python3"},
    "proof-local": {"python3", "iverilog", "vvp"},
    "board-impl": {"python3", "vivado"},
}

TOOLS = {
    "python3": ["source", "proof-local", "board-impl"],
    "iverilog": ["proof-local"],
    "vvp": ["proof-local"],
    "make": ["source", "proof-local", "board-impl"],
    "vivado": ["board-impl"],
    "verilator": [],
    "gtkwave": [],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local toolchain")
    parser.add_argument(
        "--mode",
        choices=["source", "proof-local", "board-impl"],
        required=True,
    )
    args = parser.parse_args()

    required = MODE_REQUIRED[args.mode]
    tools: dict[str, dict[str, object]] = {}
    pass_all = True

    for tool, required_for in TOOLS.items():
        path = shutil.which(tool)
        found = path is not None
        tools[tool] = {
            "required_for": required_for,
            "found": found,
            "path": path,
        }
        if tool in required and not found:
            pass_all = False

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "pass": pass_all,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "command": (
            "python3 scripts/check_local_toolchain.py "
            f"--mode {args.mode}"
        ),
        "source_tree_hash": compute_source_tree_hash(PROJECT_ROOT),
        "log_file": str(REPORT_MD.relative_to(PROJECT_ROOT).as_posix()),
        "tools": tools,
    }
    REPORT_JSON.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Local Toolchain Summary",
        "",
        f"Mode: `{args.mode}`",
        f"Pass: **{pass_all}**",
        "",
        "| Tool | Found | Path | Required For |",
        "|---|---:|---|---|",
    ]
    for tool, item in tools.items():
        required_for_vals: Any = item["required_for"]
        required_for_str = ""
        if isinstance(required_for_vals, list):
            required_for_str = ", ".join(str(v) for v in required_for_vals)
        lines.append(
            f"| {tool} | {item['found']} | {item['path']} "
            f"| {required_for_str} |"
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not pass_all:
        missing = [t for t in sorted(required) if not tools[t]["found"]]
        print("toolchain-fail: missing required tools:")
        for m in missing:
            print(f"  {m}")
        return 1

    print("toolchain-pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
