#!/usr/bin/env python3
"""Compile and run PRBS datapath end-to-end simulation."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from hash_source_tree import compute_source_tree_hash  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = PROJECT_ROOT / "reports" / "prbs_datapath_sim_summary.json"
REPORT_MD = PROJECT_ROOT / "reports" / "prbs_datapath_sim_summary.md"
REPORT_LOG = PROJECT_ROOT / "reports" / "prbs_datapath_sim.log"

RTL_SRCS = [
    "rtl/prbs_gen.v",
    "rtl/safety_monitor.v",
    "rtl/telemetry_counter.v",
    "rtl/health_monitor.v",
    "rtl/axis_skid_buffer.v",
    "rtl/axis_packet_fifo.v",
    "rtl/packer_axis.v",
    "rtl/poly_eval.v",
    "rtl/soft_weighting.v",
    "rtl/gkp_decoder.v",
    "rtl/gkp_decoder_4q_wrapper.v",
    "rtl/waveform_control_4q_top.v",
]


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
        "sim": "prbs_datapath",
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
        "# PRBS Datapath Simulation Summary",
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
        "sim/build/tb_prbs_datapath.vvp",
        "sim/tb_prbs_datapath.sv",
    ] + RTL_SRCS
    run_cmd = ["vvp", "sim/build/tb_prbs_datapath.vvp"]
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

    lut = PROJECT_ROOT / "rtl" / "reciprocal_lut_w16_q24w25.mem"
    if not lut.exists():
        gen = run(["python3", "scripts/generate_reciprocal_lut.py"])
        print(gen.stdout, end="")
        if gen.returncode != 0:
            write_summary(
                passed=False,
                returncode=gen.returncode,
                output=gen.stdout,
                command=command,
                tool_ver="unknown",
                vvp_ver="unknown",
            )
            return gen.returncode

    # soft_weighting.v reads this file by default name from simulator cwd.
    lut_root = PROJECT_ROOT / "reciprocal_lut_w16_q24w25.mem"
    if not lut_root.exists() or lut_root.read_bytes() != lut.read_bytes():
        lut_root.write_bytes(lut.read_bytes())

    iverilog_ver = tool_version(["iverilog", "-V"])
    vvp_ver = tool_version(["vvp", "-V"])

    build_dir = PROJECT_ROOT / "sim" / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    out = build_dir / "tb_prbs_datapath.vvp"
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
        and "TB_PASS tb_prbs_datapath" in run_proc.stdout
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
