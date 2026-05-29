#!/usr/bin/env python3
"""Run `make validate` and persist full stdout/stderr as proof log."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = PROJECT_ROOT / "reports" / "make_validate.log"


def main() -> int:
    subprocess.run(
        ["python3", "scripts/clean_generated_artifacts.py"],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    proc = subprocess.run(
        ["make", "validate"],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(proc.stdout, encoding="utf-8")

    print(proc.stdout, end="")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
