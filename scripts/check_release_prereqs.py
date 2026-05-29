#!/usr/bin/env python3
"""Strict release prerequisite checks for Waveform Brain."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from hash_source_tree import compute_source_tree_hash  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_REPORTS_LOCAL = [
    "reports/preboard_local_summary.json",
    "reports/preboard_local_summary.md",
    "reports/local_toolchain_summary.json",
    "reports/source_tree_hash_summary.json",
    "reports/source_tree_hash.txt",
    "reports/source_tree_clean_summary.json",
    "reports/cdc_static_summary.json",
    "reports/axilite_regfile_sim_summary.json",
    "reports/packer_axis_sim_summary.json",
    "reports/safety_monitor_sim_summary.json",
    "reports/prbs_datapath_sim_summary.json",
    "reports/gkp_decoder_sim_summary.json",
    "reports/register_map.json",
    "reports/gkp_decoder_sim.log",
    "reports/unittest.log",
    "reports/make_validate.log",
]

REQUIRED_REPORTS_BOARD = [
    "reports/implementation_gate_summary.json",
    "reports/implementation_gate_summary.md",
    "reports/board_smoke_summary.json",
    "reports/board_capture_summary.json",
    "reports/cdc_critical_summary.json",
    "reports/cdc_cell_match_summary.md",
    "reports/timing_summary.rpt",
    "reports/drc.rpt",
    "reports/cdc_full.rpt",
    "reports/cdc_critical.rpt",
    "reports/clock_interaction.rpt",
    "reports/utilization.rpt",
    "reports/vivado_synth.log",
    "reports/vivado_impl.log",
]

SIM_REPORTS = [
    "reports/axilite_regfile_sim_summary.json",
    "reports/packer_axis_sim_summary.json",
    "reports/safety_monitor_sim_summary.json",
    "reports/prbs_datapath_sim_summary.json",
    "reports/gkp_decoder_sim_summary.json",
]

REQUIRED_IMPL_CHECKS = [
    "cdc_critical",
    "cdc_cell_match",
    "timing",
    "drc",
]

HASH_STAMPED_JSONS = [
    "reports/preboard_local_summary.json",
    "reports/local_toolchain_summary.json",
    "reports/source_tree_hash_summary.json",
    "reports/source_tree_clean_summary.json",
    "reports/cdc_static_summary.json",
    "reports/axilite_regfile_sim_summary.json",
    "reports/packer_axis_sim_summary.json",
    "reports/safety_monitor_sim_summary.json",
    "reports/prbs_datapath_sim_summary.json",
    "reports/gkp_decoder_sim_summary.json",
]


def _summary_path(mode: str) -> Path:
    suffix = "local" if mode == "proof-local" else "board"
    return PROJECT_ROOT / f"reports/release_prereq_summary_{suffix}.json"


def _write_summary(*, mode: str, checks: list[dict[str, object]]) -> None:
    report = {
        "schema_version": 1,
        "mode": mode,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": (
            "python3 scripts/check_release_prereqs.py "
            f"--mode {mode}"
        ),
        "pass": all(bool(item.get("pass", False)) for item in checks),
        "checks": checks,
    }
    path = _summary_path(mode)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _ok(name: str) -> dict[str, object]:
    return {
        "name": name,
        "pass": True,
        "code": "OK",
        "message": "pass",
    }


def _fail(name: str, code: str, message: str) -> dict[str, object]:
    return {
        "name": name,
        "pass": False,
        "code": code,
        "message": message,
    }


def require_tools() -> dict[str, object]:
    missing = [
        tool
        for tool in ["iverilog", "vvp"]
        if shutil.which(tool) is None
    ]
    if missing:
        return _fail(
            "tools",
            "MISSING_SIM_TOOLS",
            "missing simulator tools for release flow: "
            + ", ".join(missing),
        )
    return _ok("tools")


def required_reports_for_mode(mode: str) -> list[str]:
    required = list(REQUIRED_REPORTS_LOCAL)
    if mode == "proof-board":
        required.extend(REQUIRED_REPORTS_BOARD)
    return required


def require_reports(mode: str) -> dict[str, object]:
    missing = [
        rel
        for rel in required_reports_for_mode(mode)
        if not (PROJECT_ROOT / rel).exists()
    ]
    if missing:
        if mode == "proof-local":
            code = "MISSING_LOCAL_REPORTS"
        else:
            code = "MISSING_BOARD_REPORTS"
        return _fail(
            "required_reports",
            code,
            "missing required reports: " + ", ".join(missing),
        )
    return _ok("required_reports")


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        return data
    return None


def _extract_hash(payload: dict[str, object]) -> str:
    value = payload.get("source_tree_hash")
    if isinstance(value, str) and value.strip():
        return value.strip()
    value = payload.get("source_sha256")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


def require_hash_consistency() -> dict[str, object]:
    canonical_summary_path = (
        PROJECT_ROOT / "reports/source_tree_hash_summary.json"
    )
    canonical_summary = _read_json(canonical_summary_path)
    if canonical_summary is None:
        return _fail(
            "hash_consistency",
            "MALFORMED_HASH_SUMMARY",
            "reports/source_tree_hash_summary.json malformed or missing",
        )

    canonical_hash = _extract_hash(canonical_summary)
    if not canonical_hash:
        return _fail(
            "hash_consistency",
            "MISSING_CANONICAL_HASH",
            "source_tree_hash_summary.json missing source_tree_hash",
        )

    hash_txt_path = PROJECT_ROOT / "reports/source_tree_hash.txt"
    try:
        hash_txt = hash_txt_path.read_text(encoding="utf-8").strip()
    except OSError:
        return _fail(
            "hash_consistency",
            "MISSING_HASH_TEXT",
            "reports/source_tree_hash.txt missing",
        )

    if hash_txt != canonical_hash:
        return _fail(
            "hash_consistency",
            "HASH_TEXT_MISMATCH",
            "reports/source_tree_hash.txt does not match "
            "reports/source_tree_hash_summary.json",
        )

    fresh_hash = compute_source_tree_hash(PROJECT_ROOT)
    if fresh_hash != canonical_hash:
        return _fail(
            "hash_consistency",
            "STALE_SOURCE_HASH",
            "reported source_tree_hash does not match "
            "freshly computed source tree hash",
        )

    for rel in HASH_STAMPED_JSONS:
        payload = _read_json(PROJECT_ROOT / rel)
        if payload is None:
            return _fail(
                "hash_consistency",
                "MALFORMED_HASH_STAMPED_SUMMARY",
                f"{rel} malformed or missing",
            )
        current_hash = _extract_hash(payload)
        if not current_hash:
            return _fail(
                "hash_consistency",
                "MISSING_HASH_FIELD",
                f"{rel} missing source_tree_hash/source_sha256",
            )
        if current_hash != canonical_hash:
            return _fail(
                "hash_consistency",
                "HASH_STAMP_MISMATCH",
                f"{rel} hash mismatch vs "
                "reports/source_tree_hash_summary.json",
            )

    return _ok("hash_consistency")


def require_preboard_pass() -> dict[str, object]:
    path = PROJECT_ROOT / "reports/preboard_local_summary.json"
    summary = _read_json(path)
    if summary is None:
        return _fail(
            "preboard",
            "MALFORMED_PREBOARD_SUMMARY",
            "preboard_local_summary.json malformed or missing",
        )
    data = summary

    if not bool(data.get("pass", False)):
        return _fail(
            "preboard",
            "PREBOARD_PASS_FALSE",
            "preboard_local_summary.json reports pass=false",
        )
    if not bool(data.get("overall_pass", False)):
        return _fail(
            "preboard",
            "PREBOARD_OVERALL_FALSE",
            "preboard_local_summary.json reports overall_pass=false",
        )

    checks_obj = data.get("checks")
    checks = checks_obj if isinstance(checks_obj, list) else []
    cosim_checks = [
        item
        for item in checks
        if "scripts/run_gkp_cosim.py" in str(item.get("cmd", ""))
    ]
    if not cosim_checks:
        return _fail(
            "preboard",
            "MISSING_COSIM_CHECK",
            "no run_gkp_cosim check found in preboard summary",
        )

    latest = cosim_checks[-1]
    if not bool(latest.get("required", False)):
        return _fail(
            "preboard",
            "COSIM_NOT_REQUIRED",
            "run_gkp_cosim was optional during preboard; release requires it",
        )
    if not bool(latest.get("raw_pass", False)):
        return _fail(
            "preboard",
            "COSIM_RAW_FAIL",
            "run_gkp_cosim did not pass in preboard summary",
        )

    return _ok("preboard")


def require_implementation_pass() -> dict[str, object]:
    path = PROJECT_ROOT / "reports/implementation_gate_summary.json"
    summary = _read_json(path)
    if summary is None:
        return _fail(
            "implementation",
            "MALFORMED_IMPL_SUMMARY",
            "implementation_gate_summary.json malformed or missing",
        )
    data = summary
    if not bool(data.get("pass", False)):
        return _fail(
            "implementation",
            "IMPL_PASS_FALSE",
            "implementation_gate_summary.json reports pass=false",
        )

    checks = data.get("checks")
    if not isinstance(checks, dict):
        return _fail(
            "implementation",
            "MISSING_IMPL_CHECKS_OBJECT",
            "implementation_gate_summary.json missing checks object",
        )

    for check_name in REQUIRED_IMPL_CHECKS:
        check_data = checks.get(check_name)
        if not isinstance(check_data, dict):
            return _fail(
                "implementation",
                "MISSING_IMPL_CHECK",
                "implementation_gate_summary missing check: " + check_name,
            )
        if not bool(check_data.get("pass", False)):
            return _fail(
                "implementation",
                "IMPL_CHECK_FAILED",
                "implementation gate check failed: " + check_name,
            )

    return _ok("implementation")


def require_simulation_pass() -> dict[str, object]:
    for rel in SIM_REPORTS:
        path = PROJECT_ROOT / rel
        payload = _read_json(path)
        if payload is None:
            return _fail(
                "simulations",
                "MALFORMED_SIM_SUMMARY",
                f"{rel} malformed or missing",
            )
        data = payload
        if not bool(data.get("pass", False)):
            return _fail(
                "simulations",
                "SIM_PASS_FALSE",
                f"{rel} reports pass=false",
            )
    return _ok("simulations")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check release prerequisites for proof-local or proof-board"
        )
    )
    parser.add_argument(
        "--mode",
        choices=["proof-local", "proof-board"],
        default="proof-board",
        help="Select prereq strictness level",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks: list[Callable[[], dict[str, object]]] = [
        require_tools,
        lambda: require_reports(args.mode),
        require_preboard_pass,
        require_hash_consistency,
        require_simulation_pass,
    ]
    if args.mode == "proof-board":
        checks.append(require_implementation_pass)

    results: list[dict[str, object]] = []
    for check in checks:
        result = check()
        results.append(result)
        if not bool(result.get("pass", False)):
            _write_summary(mode=args.mode, checks=results)
            print(
                "release-prereq-fail: "
                f"[{result.get('code', 'UNKNOWN')}] "
                f"{result.get('message', 'check failed')}"
            )
            return 1

    _write_summary(mode=args.mode, checks=results)
    print(f"release-prereq-pass mode={args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
