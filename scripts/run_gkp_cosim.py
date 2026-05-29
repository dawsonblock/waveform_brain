#!/usr/bin/env python3
"""
Run the GKP decoder RTL/golden co-simulation harness.

Requires Icarus Verilog with SystemVerilog support (`iverilog` and `vvp`).
If the tools are not installed, this script exits with code 2 and explains what
is missing. It is intentionally optional because Vivado simulation may be used
instead.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_LOG = PROJECT_ROOT / "reports" / "cosim_gkp.log"
REPORT_JSON = PROJECT_ROOT / "reports" / "cosim_gkp_summary.json"


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(str(c) for c in cmd))
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def tool_version(cmd: list[str]) -> str:
    proc = run(cmd, cwd=PROJECT_ROOT)
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
    REPORT_LOG.parent.mkdir(parents=True, exist_ok=True)
    REPORT_LOG.write_text(output, encoding="utf-8")
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sim": "gkp_cosim",
        "pass": passed,
        "tool": "iverilog",
        "tool_version": tool_ver,
        "vvp_version": vvp_ver,
        "command": command,
        "log": str(REPORT_LOG.relative_to(PROJECT_ROOT)),
        "returncode": returncode,
    }
    REPORT_JSON.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser_desc = "Run GKP decoder co-simulation."
    parser = argparse.ArgumentParser(description=parser_desc)
    parser.add_argument(
        "--vectors",
        type=Path,
        default=PROJECT_ROOT / "sim" / "gkp_cosim_vectors.hex",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=64,
    )
    parser.add_argument(
        "--profile",
        choices=["default", "edge"],
        default="default",
        help="Vector profile when generating vectors.",
    )
    parser.add_argument(
        "--use-existing-vectors",
        action="store_true",
        help="Skip vector generation and use --vectors as-is.",
    )
    args = parser.parse_args()

    all_output: list[str] = []
    executed_cmds: list[str] = []

    if shutil.which("iverilog") is None or shutil.which("vvp") is None:
        msg = (
            "ERROR: iverilog/vvp not found. "
            "Install Icarus Verilog or run this harness in Vivado simulator."
        )
        print(msg)
        write_summary(
            passed=False,
            returncode=2,
            output=msg + "\n",
            command=["python3", "scripts/run_gkp_cosim.py"],
            tool_ver="missing",
            vvp_ver="missing",
        )
        return 2

    iverilog_ver = tool_version(["iverilog", "-V"])
    vvp_ver = tool_version(["vvp", "-V"])

    build = PROJECT_ROOT / "sim" / "build"
    build.mkdir(parents=True, exist_ok=True)

    if not args.use_existing_vectors:
        # Generate vectors.
        rc = run(
            [
                sys.executable,
                "scripts/generate_gkp_cosim_vectors.py",
                "--out",
                str(args.vectors),
                "--count",
                str(args.count),
                "--profile",
                args.profile,
            ],
            cwd=PROJECT_ROOT,
        )
        print(rc.stdout, end="")
        all_output.append(rc.stdout)
        executed_cmds.append("python3 scripts/generate_gkp_cosim_vectors.py")
        if rc.returncode != 0:
            write_summary(
                passed=False,
                returncode=rc.returncode,
                output="\n".join(all_output),
                command=executed_cmds,
                tool_ver=iverilog_ver,
                vvp_ver=vvp_ver,
            )
            return rc.returncode
    elif not args.vectors.exists():
        print(f"ERROR: vector file does not exist: {args.vectors}")
        return 2

    # Generate the reciprocal ROM if the compact source package
    # does not contain it.
    rom_src = PROJECT_ROOT / "rtl" / "reciprocal_lut_w16_q24w25.mem"
    if not rom_src.exists():
        rc = run(
            [sys.executable, "scripts/generate_reciprocal_lut.py"],
            cwd=PROJECT_ROOT,
        )
        print(rc.stdout, end="")
        all_output.append(rc.stdout)
        executed_cmds.append("python3 scripts/generate_reciprocal_lut.py")
        if rc.returncode != 0:
            write_summary(
                passed=False,
                returncode=rc.returncode,
                output="\n".join(all_output),
                command=executed_cmds,
                tool_ver=iverilog_ver,
                vvp_ver=vvp_ver,
            )
            return rc.returncode

    # $readmemh in soft_weighting.v uses the default ROM filename. Make a copy
    # in the project root for simulator working-directory compatibility.
    rom_dst = PROJECT_ROOT / "reciprocal_lut_w16_q24w25.mem"
    if not rom_dst.exists() or rom_dst.read_bytes() != rom_src.read_bytes():
        rom_dst.write_bytes(rom_src.read_bytes())

    out = build / "gkp_cosim.vvp"
    sources = [
        "sim/tb_gkp_decoder_cosim.sv",
        "rtl/gkp_decoder.v",
        "rtl/poly_eval.v",
        "rtl/soft_weighting.v",
    ]

    compile_cmd = ["iverilog", "-g2012", "-Wall", "-o", str(out)] + sources
    exec_cmd = ["vvp", str(out), f"+VECTORS={args.vectors}"]

    rc = run(compile_cmd, cwd=PROJECT_ROOT)
    print(rc.stdout, end="")
    all_output.append(rc.stdout)
    executed_cmds.append(" ".join(compile_cmd))
    if rc.returncode != 0:
        write_summary(
            passed=False,
            returncode=rc.returncode,
            output="\n".join(all_output),
            command=executed_cmds,
            tool_ver=iverilog_ver,
            vvp_ver=vvp_ver,
        )
        return rc.returncode

    rc = run(exec_cmd, cwd=PROJECT_ROOT)
    print(rc.stdout, end="")
    all_output.append(rc.stdout)
    executed_cmds.append(" ".join(exec_cmd))
    passed = (
        rc.returncode == 0
        and "COSIM SUMMARY: pass=" in rc.stdout
        and "fail=0" in rc.stdout
    )
    write_summary(
        passed=passed,
        returncode=rc.returncode,
        output="\n".join(all_output),
        command=executed_cmds,
        tool_ver=iverilog_ver,
        vvp_ver=vvp_ver,
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
