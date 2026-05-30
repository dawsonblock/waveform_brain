#!/usr/bin/env python3
"""Fail if source tree contains forbidden generated or transient artifacts."""

from __future__ import annotations

import fnmatch
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_NAMES = {
    "__MACOSX",
    ".DS_Store",
    "__pycache__",
    ".pytest_cache",
}

FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".jou",
    ".str",
    ".wdb",
    ".vcd",
    ".fst",
}

FORBIDDEN_REL_PATTERNS = [
    "sim/build",
    "build_dir",
    "dist/*.zip",
    "rtl/reciprocal_lut_w16_q24w25.mem",
    "reciprocal_lut_w16_q24w25.mem",
    "register_map.json",
    "register_map.md",
    "register_map_issues.log",
    "cdc_crossing_suggestions.json",
    "cdc_crossing_suggestions.md",
    "sim/gkp_cosim_vectors.hex",
]

ALLOWED_REPORT_LOGS = {
    "reports/make_validate.log",
    "reports/unittest.log",
    "reports/cosim_gkp.log",
    "reports/axilite_regfile_sim.log",
    "reports/packer_axis_sim.log",
    "reports/safety_monitor_sim.log",
    "reports/prbs_datapath_sim.log",
    "reports/cdc_cosim.log",
}


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def is_forbidden_by_pattern(rel_path: str) -> bool:
    for pattern in FORBIDDEN_REL_PATTERNS:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if rel_path == pattern or rel_path.startswith(pattern + "/"):
            return True
    return False


def scan_tree() -> list[str]:
    findings: list[str] = []
    for path in PROJECT_ROOT.rglob("*"):
        if ".git" in path.parts:
            continue

        rel_path = rel(path)
        name = path.name

        if name in FORBIDDEN_NAMES:
            findings.append(f"forbidden_name: {rel_path}")

        if path.is_file() and path.suffix in FORBIDDEN_SUFFIXES:
            findings.append(f"forbidden_suffix: {rel_path}")

        if is_forbidden_by_pattern(rel_path):
            findings.append(f"forbidden_pattern: {rel_path}")

        if (
            path.is_file()
            and path.suffix == ".log"
            and rel_path.startswith("reports/")
        ):
            if rel_path not in ALLOWED_REPORT_LOGS:
                findings.append(f"forbidden_report_log: {rel_path}")

    return sorted(set(findings))


def main() -> int:
    findings = scan_tree()
    if findings:
        print("source-tree-clean: FAIL")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("source-tree-clean: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
