#!/usr/bin/env python3
"""Compile and run q15_16_mult behavioral simulation."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from hash_source_tree import compute_source_tree_hash  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = PROJECT_ROOT / "reports" / "q15_16_mult_sim_summary.json"
REPORT_MD = PROJECT_ROOT / "reports" / "q15_16_mult_sim_summary.md"
REPORT_LOG = PROJECT_ROOT / "reports" / "q15_16_mult_sim.log"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd))
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def tool_version(cmd: list[str]) -> str:
    proc = run(cmd)
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            return line
    return "unknown"


def write_summary(
    *,
    passed: bool,
    returncode: int,
    output: str,
    command: list[str],
    tool_ver: str,
    vvp_ver: str,
) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_LOG.write_text(output, encoding="utf-8")
    stdout_tail = "\n".join(output.splitlines()[-40:])

    summary = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sim": "q15_16_mult",
        "pass": passed,
        "tool": "iverilog",
        "tool_version": tool_ver,
        "vvp_version": vvp_ver,
        "command": " && ".join(command),
        "source_tree_hash": compute_source_tree_hash(PROJECT_ROOT),
        "log_file": str(REPORT_LOG.relative_to(PROJECT_ROOT)),
        "returncode": returncode,
        "stdout_tail": stdout_tail,
    }
    REPORT_JSON.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# q15_16_mult Simulation Summary",
        "",
        f"Timestamp UTC: `{summary['generated_at_utc']}`",
        "",
        f"Pass: **{passed}**",
        f"Return code: `{returncode}`",
        "Tool: `iverilog`",
        f"Icarus version: `{tool_ver}`",
        f"VVP version: `{vvp_ver}`",
        f"Log: `{summary['log_file']}`",
        "",
        "## Output tail",
        "",
        "```text",
        stdout_tail,
        "```",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    compile_cmd = [
        "iverilog",
        "-g2012",
        "-Wall",
        "-o",
        "sim/build/tb_q15_16_mult.vvp",
        "sim/tb_q15_16_mult.sv",
        "rtl/q15_16_mult.v",
    ]
    run_cmd = ["vvp", "sim/build/tb_q15_16_mult.vvp"]
    command = compile_cmd + ["&&"] + run_cmd

    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        msg = (
            "ERROR: iverilog/vvp not found. "
            "Install Icarus Verilog or use Vivado xsim."
        )
        print(msg)
        write_summary(
            passed=False,
            returncode=2,
            output=msg + "\n",
            command=command,
            tool_ver="missing",
            vvp_ver="missing",
        )
        return 2

    iverilog_ver = tool_version(["iverilog", "-V"])
    vvp_ver = tool_version(["vvp", "-V"])

    build_dir = PROJECT_ROOT / "sim" / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    out = build_dir / "tb_q15_16_mult.vvp"
    compile_cmd[4] = str(out)
    run_cmd[1] = str(out)
    command = compile_cmd + ["&&"] + run_cmd

    compile_proc = run(compile_cmd)
    print(compile_proc.stdout, end="")
    if compile_proc.returncode != 0:
        write_summary(
            passed=False,
            returncode=compile_proc.returncode,
            output=compile_proc.stdout,
            command=command,
            tool_ver=iverilog_ver,
            vvp_ver=vvp_ver,
        )
        return compile_proc.returncode

    run_proc = run(run_cmd)
    print(run_proc.stdout, end="")
    combined = compile_proc.stdout + "\n" + run_proc.stdout
    passed = (
        run_proc.returncode == 0
        and "TB_PASS tb_q15_16_mult" in run_proc.stdout
    )
    write_summary(
        passed=passed,
        returncode=run_proc.returncode,
        output=combined,
        command=command,
        tool_ver=iverilog_ver,
        vvp_ver=vvp_ver,
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
