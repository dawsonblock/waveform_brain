#!/usr/bin/env python3
"""
Waveform Brain v1.0 — Vivado Implementation Report Gate

Consumes Vivado-generated reports and decides whether board-level
verification is allowed to proceed.

Required reports:
  reports/cdc_critical_summary.json
  reports/cdc_cell_match_summary.md
  reports/timing_summary.rpt
  reports/drc.rpt

Optional reports:
  reports/utilization.rpt
  reports/clock_interaction.rpt
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def read_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def cdc_pass(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing cdc_critical_summary.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "malformed cdc_critical_summary.json"
    return (
        bool(data.get("pass", False)),
        f"critical_total={data.get('critical_total', 'unknown')}",
    )


def cell_match_pass(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing cdc_cell_match_summary.md"
    text = read_text(path)
    # Any markdown row with "| 0 |" after the header is a failed
    # required match.
    zero_rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        if set(line.replace("|", "").strip()) <= {"-", ":"}:
            continue
        if "`" in line:
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 2:
                raw_count = cols[1].replace("`", "").strip().lower()
                try:
                    count = int(raw_count, 0)
                except ValueError:
                    continue
                if count == 0:
                    zero_rows.append(line)
    return len(zero_rows) == 0, f"zero_match_rows={len(zero_rows)}"


def timing_pass(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing timing_summary.rpt"
    text = read_text(path)
    # Conservative parsing. If there are explicit timing failures, fail.
    fail_patterns = [
        r"timing constraints are not met",
        r"VIOLATED",
        r"Slack \(VIOLATED\)",
    ]
    if any(re.search(p, text, re.IGNORECASE) for p in fail_patterns):
        return False, "timing violation text found"

    required_metrics = {
        "WNS": [r"\bWNS\(ns\)\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)"],
        "TNS": [r"\bTNS\(ns\)\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)"],
        "WHS": [r"\bWHS\(ns\)\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)"],
        "THS": [r"\bTHS\(ns\)\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)"],
        "WPWS": [r"\bWPWS\(ns\)\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)"],
        "TPWS": [r"\bTPWS\(ns\)\s*[:=]?\s*([-+]?\d+(?:\.\d+)?)"],
    }

    parsed_metrics: dict[str, float] = {}
    missing_metrics: list[str] = []
    for metric, patterns in required_metrics.items():
        value = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                break
        if value is None:
            missing_metrics.append(metric)
        else:
            parsed_metrics[metric] = value

    if missing_metrics:
        return False, f"missing timing metrics: {','.join(missing_metrics)}"

    negative_metrics = [
        f"{metric}={parsed_metrics[metric]:.3f}"
        for metric in ["WNS", "TNS", "WHS", "THS", "WPWS", "TPWS"]
        if parsed_metrics[metric] < 0.0
    ]
    if negative_metrics:
        return False, f"negative timing metrics: {', '.join(negative_metrics)}"

    detail = ", ".join(
        f"{metric}={parsed_metrics[metric]:.3f}"
        for metric in ["WNS", "TNS", "WHS", "THS", "WPWS", "TPWS"]
    )
    return True, detail


def drc_pass(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing drc.rpt"
    text = read_text(path)
    fail_class_patterns = {
        "NSTD": r"\bNSTD(?:-[0-9]+)?\b",
        "UCIO": r"\bUCIO(?:-[0-9]+)?\b",
        "LUTLP": r"\bLUTLP(?:-[0-9]+)?\b",
        "MDRV": r"\bMDRV(?:-[0-9]+)?\b",
        "UNCONSTRAINED_PATH": r"unconstrained\s+path",
    }

    class_hits = {
        name: len(re.findall(pattern, text, re.IGNORECASE))
        for name, pattern in fail_class_patterns.items()
    }
    fail_hits = {name: count for name, count in class_hits.items() if count > 0}
    if fail_hits:
        detail = ", ".join(
            f"{name}={count}" for name, count in sorted(fail_hits.items())
        )
        return False, f"drc_fail_classes: {detail}"

    critical = len(
        re.findall(r"Critical Warning|CRITICAL WARNING|ERROR:", text)
    )
    return critical == 0, f"critical_or_error_count={critical}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate board readiness from Vivado reports."
    )
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("reports/implementation_gate_summary.json"),
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=Path("reports/implementation_gate_summary.md"),
    )
    args = parser.parse_args()

    r = args.reports
    checks = {
        "cdc_critical": cdc_pass(r / "cdc_critical_summary.json"),
        "cdc_cell_match": cell_match_pass(r / "cdc_cell_match_summary.md"),
        "timing": timing_pass(r / "timing_summary.rpt"),
        "drc": drc_pass(r / "drc.rpt"),
    }

    overall = all(v[0] for v in checks.values())

    checks_summary = {
        k: {"pass": v[0], "detail": v[1]}
        for k, v in checks.items()
    }

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "pass": overall,
        "checks": checks_summary,
        "required_reports": [
            "cdc_critical_summary.json",
            "cdc_cell_match_summary.md",
            "timing_summary.rpt",
            "drc.rpt",
        ],
        "optional_reports": [
            "cdc_full.rpt",
            "clock_interaction.rpt",
            "utilization.rpt",
        ],
    }

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Implementation Gate Summary",
        "",
        f"Timestamp UTC: `{summary['timestamp_utc']}`",
        "",
        f"Overall pass: **{overall}**",
        "",
        "| Gate | Pass | Detail |",
        "|---|---:|---|",
    ]
    for name, result in checks_summary.items():
        lines.append(f"| {name} | {result['pass']} | {result['detail']} |")
    lines.append("")
    lines.append("Board testing is blocked unless every gate passes.")
    args.md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(args.md_out.read_text(encoding="utf-8"))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
