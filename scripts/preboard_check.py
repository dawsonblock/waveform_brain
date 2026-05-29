#!/usr/bin/env python3
"""
Waveform Brain v1.0 — Local Pre-Board Check

Runs all non-Vivado checks that can be performed before implementation.

v0.16 correction:
  - Cleans generated compact-package artifacts before static/unit tests.
  - Runs tests before regenerating the reciprocal LUT and co-sim vectors.
  - Prevents test_compact_package.py from failing after generator execution.

This does not prove timing, CDC, or hardware behavior. It verifies that the
source tree is internally consistent, generated artifacts are reproducible, and
the known pre-board inputs exist.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from hash_source_tree import compute_source_tree_hash  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "reports"
SUMMARY_JSON = REPORT_DIR / "preboard_local_summary.json"
SUMMARY_MD = REPORT_DIR / "preboard_local_summary.md"


def source_hash() -> str:
    return compute_source_tree_hash(PROJECT_ROOT)


def clean_generated_artifacts() -> None:
    subprocess.run(
        [sys.executable, "scripts/clean_generated_artifacts.py"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    for cache_dir in PROJECT_ROOT.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir, ignore_errors=True)
    shutil.rmtree(PROJECT_ROOT / "sim" / "build", ignore_errors=True)
    stale_logs = [
        "reports/source_tree_clean.log",
        "reports/local_toolchain.log",
        "reports/rtl_sanity.log",
        "reports/rtl_arithmetic_audit.log",
        "reports/cdc_static.log",
        "reports/source_tree_hash.log",
        "reports/gkp_decoder_sim.log",
    ]
    for rel in stale_logs:
        p = PROJECT_ROOT / rel
        if p.exists():
            p.unlink()


def write_log(rel_path: str, content: str) -> None:
    path = PROJECT_ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(
    cmd: list[str],
    *,
    required: bool = True,
    timeout: int = 120,
    log_rel: str | None = None,
) -> dict[str, object]:
    print("+", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        ok = proc.returncode == 0
        if not ok:
            print(proc.stdout)
        if log_rel is not None:
            write_log(log_rel, proc.stdout)
        return {
            "cmd": " ".join(cmd),
            "required": required,
            "returncode": proc.returncode,
            "pass": ok if required else True,
            "raw_pass": ok,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "command": " ".join(cmd),
            "source_tree_hash": source_hash(),
            "log_file": log_rel,
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-25:]),
        }
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        out += f"\nTimed out after {timeout} seconds."
        print(out)
        if log_rel is not None:
            write_log(log_rel, out)
        return {
            "cmd": " ".join(cmd),
            "required": required,
            "returncode": 124,
            "pass": False if required else True,
            "raw_pass": False,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "command": " ".join(cmd),
            "source_tree_hash": source_hash(),
            "log_file": log_rel,
            "stdout_tail": "\n".join(out.splitlines()[-25:]),
        }


def exists(rel: str) -> dict:
    p = PROJECT_ROOT / rel
    return {
        "path": rel,
        "exists": p.exists(),
        "size": p.stat().st_size if p.exists() else 0,
    }


def main() -> int:
    mode = "proof"
    if "--mode" in sys.argv:
        try:
            mode = sys.argv[sys.argv.index("--mode") + 1]
        except IndexError:
            print("ERROR: --mode requires one of: explore, proof")
            return 2
    if mode not in {"explore", "proof"}:
        print("ERROR: --mode requires one of: explore, proof")
        return 2

    REPORT_DIR.mkdir(exist_ok=True)

    # Keep compact-package tests meaningful even if a previous local run left
    # generated artifacts behind.
    clean_generated_artifacts()

    checks: list[dict[str, object]] = []
    files: list[dict[str, object]] = []

    required_files = [
        "rtl/waveform_brain_axi4lite_cdc_top.v",
        "rtl/waveform_brain_cdc_wrapper.v",
        "rtl/axilite_regfile_full.v",
        "rtl/soft_weighting.v",
        "rtl/gkp_decoder.v",
        "rtl/poly_eval.v",
        "constraints/cdc_xpm_wrapper_constraints.xdc",
        "scripts/build_gate_cdc.tcl",
        "scripts/verify_cdc_constraints.tcl",
        "scripts/parse_cdc_report.py",
        "scripts/package_cdc_signoff.py",
        "scripts/implementation_gate.py",
        "scripts/package_vivado_signoff.py",
        "docs/PHASE1_SIGNOFF_SHEET.md",
        "docs/CDC_HARDENING_V14.md",
        "docs/PREBOARD_GATE_V15.md",
        "docs/BOARD_READY_TEMPLATE.md",
    ]

    for rel in required_files:
        files.append(exists(rel))

    checks.append(
        run(
            [sys.executable, "scripts/check_source_tree_clean.py"],
            log_rel="reports/source_tree_clean.log",
        )
    )
    checks.append(
        run(
            [
                sys.executable,
                "scripts/check_local_toolchain.py",
                "--mode",
                "proof-local",
            ],
            required=(mode == "proof"),
            log_rel="reports/local_toolchain.log",
        )
    )

    # 1) Static/unit tests run while generated heavy artifacts are absent.
    checks.append(
        run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            log_rel="reports/unittest.log",
            timeout=300,
        )
    )
    checks.append(
        run(
            [sys.executable, "scripts/rtl_sanity_check.py"],
            log_rel="reports/rtl_sanity.log",
        )
    )
    checks.append(
        run(
            [sys.executable, "scripts/audit_rtl_arithmetic.py"],
            log_rel="reports/rtl_arithmetic_audit.log",
        )
    )

    # 2) Then prove generated artifacts are reproducible.
    checks.append(run([sys.executable, "scripts/generate_reciprocal_lut.py"]))
    checks.append(
        run(
            [
                sys.executable,
                "scripts/generate_gkp_cosim_vectors.py",
                "--count",
                "16",
            ]
        )
    )
    checks.append(run([sys.executable, "scripts/extract_register_map.py"]))
    checks.append(
        run(
            [sys.executable, "scripts/analyze_cdc_crossings.py"],
            log_rel="reports/cdc_static.log",
        )
    )
    checks.append(
        run(
            [
                sys.executable,
                "scripts/verify_cdc_manifest.py",
                "--static-only",
            ],
            log_rel="reports/cdc_static.log",
        )
    )
    checks.append(
        run(
            [
                sys.executable,
                "scripts/hash_source_tree.py",
                "--out-txt",
                "reports/source_tree_hash.txt",
            ],
            log_rel="reports/source_tree_hash.log",
        )
    )
    sim_required = mode == "proof"
    checks.append(
        run(
            [sys.executable, "scripts/run_axilite_regfile_sim.py"],
            required=sim_required,
            timeout=240,
            log_rel="reports/axilite_regfile_sim.log",
        )
    )
    checks.append(
        run(
            [sys.executable, "scripts/run_packer_axis_sim.py"],
            required=sim_required,
            timeout=240,
            log_rel="reports/packer_axis_sim.log",
        )
    )
    checks.append(
        run(
            [sys.executable, "scripts/run_safety_monitor_sim.py"],
            required=sim_required,
            timeout=240,
            log_rel="reports/safety_monitor_sim.log",
        )
    )
    checks.append(
        run(
            [sys.executable, "scripts/run_prbs_datapath_sim.py"],
            required=sim_required,
            timeout=300,
            log_rel="reports/prbs_datapath_sim.log",
        )
    )
    checks.append(
        run(
            [sys.executable, "scripts/run_gkp_cosim.py", "--count", "16"],
            required=sim_required,
            timeout=240,
            log_rel="reports/gkp_decoder_sim.log",
        )
    )

    register_map_root = PROJECT_ROOT / "register_map.json"
    if register_map_root.exists():
        (REPORT_DIR / "register_map.json").write_text(
            register_map_root.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    source_tree_clean_pass = any(
        str(c.get("command", "")).endswith("check_source_tree_clean.py")
        and bool(c.get("raw_pass", False))
        for c in checks
    )
    cdc_static_pass = all(
        bool(c["raw_pass"])
        for c in checks
        if "analyze_cdc_crossings.py" in str(c.get("command"))
        or "verify_cdc_manifest.py" in str(c.get("command"))
    )

    source_clean_summary = {
        "schema_version": 1,
        "pass": source_tree_clean_pass,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python3 scripts/check_source_tree_clean.py",
        "source_tree_hash": source_hash(),
        "log_file": "reports/source_tree_clean.log",
    }
    (REPORT_DIR / "source_tree_clean_summary.json").write_text(
        json.dumps(source_clean_summary, indent=2) + "\n",
        encoding="utf-8",
    )

    cdc_static_summary = {
        "schema_version": 1,
        "pass": cdc_static_pass,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python3 scripts/analyze_cdc_crossings.py && "
        "python3 scripts/verify_cdc_manifest.py --static-only",
        "source_tree_hash": source_hash(),
        "log_file": "reports/cdc_static.log",
    }
    (REPORT_DIR / "cdc_static_summary.json").write_text(
        json.dumps(cdc_static_summary, indent=2) + "\n",
        encoding="utf-8",
    )

    file_pass = all(item["exists"] for item in files)
    check_pass = all(item["pass"] for item in checks)
    overall_pass = file_pass and check_pass

    summary = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "project_root": str(PROJECT_ROOT),
        "pass": overall_pass,
        "overall_pass": overall_pass,
        "command": f"python3 scripts/preboard_check.py --mode {mode}",
        "source_tree_hash": source_hash(),
        "log_file": "reports/preboard_local_summary.md",
        "file_pass": file_pass,
        "check_pass": check_pass,
        "files": files,
        "checks": checks,
        "vivado_required_next": [
            "Vivado elaboration",
            "report_cdc",
            "report_clock_interaction",
            "report_timing_summary",
            "report_drc",
            "report_utilization",
            "Phase 1 sign-off sheet",
        ],
    }

    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Local Pre-Board Check Summary",
        "",
        f"Timestamp UTC: `{summary['generated_at_utc']}`",
        "",
        f"Overall pass: **{overall_pass}**",
        f"File pass: **{file_pass}**",
        f"Check pass: **{check_pass}**",
        "",
        "## Required files",
        "",
        "| File | Exists | Size |",
        "|---|---:|---:|",
    ]
    for f in files:
        lines.append(f"| `{f['path']}` | {f['exists']} | {f['size']} |")

    lines += [
        "",
        "## Checks",
        "",
        "| Command | Required | Raw pass | Gate pass |",
        "|---|---:|---:|---:|",
    ]
    for c in checks:
        lines.append(
            (
                f"| `{c['cmd']}` | {c['required']} | "
                f"{c['raw_pass']} | {c['pass']} |"
            )
        )

    lines += [
        "",
        "## Next required Vivado gates",
        "",
        "- Vivado elaboration",
        "- CDC reports",
        "- Clock interaction report",
        "- Timing summary",
        "- DRC report",
        "- Utilization report",
        "- CDC sign-off package",
        "",
        "This local check does not authorize board testing.",
    ]

    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nWrote {SUMMARY_JSON}")
    print(f"Wrote {SUMMARY_MD}")
    print(f"\nLOCAL PRE-BOARD PASS: {overall_pass}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
