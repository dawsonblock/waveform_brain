#!/usr/bin/env python3
"""
Waveform Brain v1.0 — CDC Report Parser

Parses Vivado report_cdc output, writes JSON summary, and returns non-zero when
critical patterns are found.

Usage:
    python3 scripts/parse_cdc_report.py reports/cdc_full.rpt --json-out reports/cdc_full_summary.json
    python3 scripts/parse_cdc_report.py reports/cdc_critical.rpt --json-out reports/cdc_critical_summary.json --fail-on-critical
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CRITICAL_PATTERNS = [
    (r"No user constraint", "unconstrained_path"),
    (r"Unconstrained", "unconstrained_path"),
    (r"Unknown CDC structure", "unknown_cdc_structure"),
    (r"Missing set_bus_skew", "missing_bus_skew"),
    (r"missing set_bus_skew", "missing_bus_skew"),
    (r"Critical Warning", "critical_warning"),
]

WARNING_PATTERNS = [
    (r"No ASYNC_REG property", "missing_async_reg"),
    (r"CDC-10", "cdc_10_comb_logic_before_sync"),
    (r"CDC-11", "cdc_11_fanout_to_dest"),
    (r"CDC-4", "cdc_4_multibit_crossing"),
]


def collect_matches(content: str, patterns):
    result = {}
    examples = {}
    lines = content.splitlines()
    for pattern, key in patterns:
        matches = []
        regex = re.compile(pattern, re.IGNORECASE)
        for line in lines:
            if regex.search(line):
                matches.append(line.strip())
        result[key] = result.get(key, 0) + len(matches)
        examples.setdefault(key, [])
        examples[key].extend(matches[:10])
        examples[key] = examples[key][:10]
    return result, examples


def parse_report(path: Path) -> dict:
    if not path.exists():
        return {
            "report": str(path),
            "exists": False,
            "pass": False,
            "error": "report file not found",
            "critical_counts": {},
            "warning_counts": {},
            "examples": {},
        }

    content = path.read_text(encoding="utf-8", errors="ignore")
    critical_counts, critical_examples = collect_matches(content, CRITICAL_PATTERNS)
    warning_counts, warning_examples = collect_matches(content, WARNING_PATTERNS)

    critical_total = sum(critical_counts.values())
    warning_total = sum(warning_counts.values())

    # Do not double-count generic "Unconstrained" and "No user constraint" in final status
    # too aggressively. Any non-zero critical category is still a fail.
    passed = critical_total == 0

    return {
        "report": str(path),
        "exists": True,
        "pass": passed,
        "critical_total": critical_total,
        "warning_total": warning_total,
        "critical_counts": critical_counts,
        "warning_counts": warning_counts,
        "examples": {
            "critical": critical_examples,
            "warning": warning_examples,
        },
    }



def parse_cdc_report(report_path, json_out=None, md_out=None):
    """
    Backward-compatible helper used by older tests/scripts.

    Returns:
        0 when no critical CDC pattern is found
        1 when critical CDC patterns are found
        2 when the report is missing
    """
    summary = parse_report(Path(report_path))

    # Older tests expect status field.
    summary["status"] = "PASS" if summary.get("pass") else "FAIL"

    if json_out is not None:
        out = Path(json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if md_out is not None:
        out = Path(md_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# CDC Report Parser Summary",
            "",
            f"Report: `{summary.get('report')}`",
            f"Status: **{summary['status']}**",
            f"Critical total: `{summary.get('critical_total', 'n/a')}`",
            f"Warning total: `{summary.get('warning_total', 'n/a')}`",
        ]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not summary.get("exists"):
        return 2
    return 0 if summary.get("pass") else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse Vivado report_cdc output.")
    parser.add_argument("report", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args()

    summary = parse_report(args.report)

    print(f"\n=== CDC Report Summary: {args.report} ===")
    print(f"exists          : {summary['exists']}")
    print(f"pass            : {summary['pass']}")
    print(f"critical_total  : {summary.get('critical_total', 'n/a')}")
    print(f"warning_total   : {summary.get('warning_total', 'n/a')}")

    if summary["exists"]:
        print("\nCritical counts:")
        for k, v in summary["critical_counts"].items():
            print(f"  {k}: {v}")
        print("\nWarning counts:")
        for k, v in summary["warning_counts"].items():
            print(f"  {k}: {v}")
    else:
        print(f"ERROR: {summary['error']}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json_out}")

    if args.fail_on_critical and not summary["pass"]:
        return 1
    return 0 if summary["exists"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
