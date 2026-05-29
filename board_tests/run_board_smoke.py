#!/usr/bin/env python3
"""Run board smoke checks and emit summary reports."""

from __future__ import annotations

import argparse
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    _adapter_contract = importlib.import_module(
        ".adapter_contract",
        __package__,
    )
    _checks = importlib.import_module(
        ".checks",
        __package__,
    )
else:
    _adapter_contract = importlib.import_module("adapter_contract")
    _checks = importlib.import_module("checks")

ADAPTER_CONTRACT_VERSION = _adapter_contract.ADAPTER_CONTRACT_VERSION
BOARD_CAPTURE_BLOCKED_CODE = _adapter_contract.BOARD_CAPTURE_BLOCKED_CODE

axi_lite_smoke = _checks.axi_lite_smoke
axis_capture_smoke = _checks.axis_capture_smoke
config_apply_smoke = _checks.config_apply_smoke
ensure_capture_placeholders = _checks.ensure_capture_placeholders
prbs_capture_smoke = _checks.prbs_capture_smoke
read_build_id = _checks.read_build_id
safety_trip_smoke = _checks.safety_trip_smoke
telemetry_window_smoke = _checks.telemetry_window_smoke


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def markdown_summary(results: list[dict[str, object]], passed: bool) -> str:
    lines = [
        "# Board Smoke Summary",
        "",
        f"Timestamp UTC: `{utc_now()}`",
        f"Overall pass: **{passed}**",
        "",
        "| Check | Status | Pass | Reason |",
        "|---|---|---:|---|",
    ]
    for item in results:
        lines.append(
            f"| {item['name']} | {item['status']} | "
            f"{item['pass']} | {item.get('reason', '')} |"
        )
    lines.append("")
    lines.append(
        "This scaffold is fail-closed until a real board adapter is wired."
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run board smoke scaffold checks."
    )
    parser.add_argument(
        "--device",
        default="",
        help="Board device identifier used by transport adapter (future).",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory to write board smoke outputs.",
    )
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    checks = [
        read_build_id,
        axi_lite_smoke,
        config_apply_smoke,
        safety_trip_smoke,
        prbs_capture_smoke,
        axis_capture_smoke,
        telemetry_window_smoke,
    ]
    results = [check(args.device or None) for check in checks]

    overall_pass = all(bool(item.get("pass", False)) for item in results)
    blocked_count = sum(
        1 for item in results if item.get("status") == "blocked"
    )

    ensure_capture_placeholders(reports_dir)

    capture_pass = all(
        bool(item.get("pass", False))
        for item in results
        if item["name"] in {"prbs_capture_smoke", "axis_capture_smoke"}
    )
    capture_summary = {
        "timestamp_utc": utc_now(),
        "device": args.device,
        "pass": capture_pass,
        "status": "pass" if capture_pass else "blocked",
        "fail_closed": not capture_pass,
        "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
        "reason_code": (
            "OK" if capture_pass else BOARD_CAPTURE_BLOCKED_CODE
        ),
        "checks": [
            item
            for item in results
            if item["name"] in {"prbs_capture_smoke", "axis_capture_smoke"}
        ],
        "artifacts": {
            "prbs_hex": str(
                (reports_dir / "board_capture_prbs.hex").as_posix()
            ),
            "packets_jsonl": str(
                (reports_dir / "board_capture_packets.jsonl").as_posix()
            ),
        },
    }

    summary = {
        "timestamp_utc": utc_now(),
        "device": args.device,
        "pass": overall_pass,
        "status": "pass" if overall_pass else "blocked",
        "fail_closed": not overall_pass,
        "blocked_check_count": blocked_count,
        "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
        "checks": results,
        "capture_artifacts": {
            "prbs_hex": str(
                (reports_dir / "board_capture_prbs.hex").as_posix()
            ),
            "packets_jsonl": str(
                (reports_dir / "board_capture_packets.jsonl").as_posix()
            ),
        },
    }

    json_path = reports_dir / "board_smoke_summary.json"
    md_path = reports_dir / "board_smoke_summary.md"
    capture_path = reports_dir / "board_capture_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    capture_path.write_text(
        json.dumps(capture_summary, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        markdown_summary(results, overall_pass),
        encoding="utf-8",
    )

    print(f"Wrote {json_path}")
    print(f"Wrote {capture_path}")
    print(f"Wrote {md_path}")
    print("board-smoke-pass" if overall_pass else "board-smoke-fail")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
