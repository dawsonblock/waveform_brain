#!/usr/bin/env python3
"""
Waveform Brain v1.0 — RTL Arithmetic Audit

Scans synthesizable RTL for operators that are risky
in high-speed RFSoC fabric, especially runtime division/modulo.

This is a static heuristic. It does not replace synthesis timing reports.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DIV_ALLOWLIST: set[str] = set()

COMMENT_LINE_RE = re.compile(r"//.*$")
COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
DIV_OPERATOR_RE = re.compile(r"[\w\)\]]\s*/\s*[\w\(\[]")
MOD_OPERATOR_RE = re.compile(r"[\w\)\]]\s*%\s*[\w\(\[]")


def strip_comments(text: str) -> str:
    text = COMMENT_BLOCK_RE.sub("", text)
    lines = [COMMENT_LINE_RE.sub("", line) for line in text.splitlines()]
    return "\n".join(lines)


def find_ops(path: Path) -> list[dict]:
    text = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
    issues = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Remove strings.
        scrub = re.sub(r'".*?"', '""', line)

        # Runtime division/modulo operators. Avoid matching
        # part-select ranges or comments.
        if DIV_OPERATOR_RE.search(scrub):
            issues.append(
                {
                    "file": str(path),
                    "line": lineno,
                    "kind": "division_operator",
                    "text": line.strip(),
                    "severity": "critical",
                }
            )
        if MOD_OPERATOR_RE.search(scrub):
            issues.append(
                {
                    "file": str(path),
                    "line": lineno,
                    "kind": "modulo_operator",
                    "text": line.strip(),
                    "severity": "warning",
                }
            )

        # Very rough high-fanout constant assignment hint.
        if (
            re.search(r"assign\s+\w+\s*=", scrub)
            and scrub.count("&") + scrub.count("|") > 6
        ):
            issues.append(
                {
                    "file": str(path),
                    "line": lineno,
                    "kind": "large_combinational_assign",
                    "text": line.strip(),
                    "severity": "info",
                }
            )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit RTL for risky arithmetic operators."
    )
    parser.add_argument("--rtl-dir", type=Path, default=Path("rtl"))
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("reports/rtl_arithmetic_audit.json"),
    )
    parser.add_argument(
        "--md-out", type=Path, default=Path("reports/rtl_arithmetic_audit.md")
    )
    parser.add_argument(
        "--fail-on-division",
        action="store_true",
        default=True,
    )
    args = parser.parse_args()

    files = sorted(args.rtl_dir.glob("*.v"))
    issues = []
    for path in files:
        issues.extend(find_ops(path))

    critical = [i for i in issues if i["severity"] == "critical"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    summary = {
        "rtl_dir": str(args.rtl_dir),
        "files_scanned": len(files),
        "pass": len(critical) == 0,
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "issues": issues,
    }

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# RTL Arithmetic Audit",
        "",
        f"Files scanned: `{len(files)}`",
        f"Pass: **{summary['pass']}**",
        f"Critical count: `{len(critical)}`",
        f"Warning count: `{len(warnings)}`",
        "",
        "| Severity | Kind | File | Line | Text |",
        "|---|---|---|---:|---|",
    ]
    for issue in issues:
        lines.append(
            (
                f"| {issue['severity']} | {issue['kind']} | "
                f"`{issue['file']}` | {issue['line']} | "
                f"`{issue['text']}` |"
            )
        )
    args.md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Scanned {len(files)} RTL files.")
    print(f"Critical issues: {len(critical)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Wrote {args.json_out}")
    print(f"Wrote {args.md_out}")

    return 1 if (args.fail_on_division and critical) else 0


if __name__ == "__main__":
    raise SystemExit(main())
