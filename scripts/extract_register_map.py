#!/usr/bin/env python3
"""
Waveform Brain v1.0 — Register Map Extractor

Extracts register definitions from firmware/registers.h and emits:
  - register_map.json
  - register_map.md
  - register_map_issues.log

This is intentionally conservative. It does not guess semantics beyond a small
keyword-based classification used for CDC review and sign-off preparation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "firmware" / "registers.h"
OUT_JSON = ROOT / "register_map.json"
OUT_MD = ROOT / "register_map.md"
OUT_LOG = ROOT / "register_map_issues.log"

DEFINE_RE = re.compile(
    r"^\s*#define\s+(WB_REG_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+|\d+)\b"
)

DESC: Dict[str, str] = {
    "WB_REG_BUILD_ID": "Build identifier",
    "WB_REG_STATUS": "Status snapshot",
    "WB_REG_FAULT_FLAGS": "Latched fault flags",
    "WB_REG_PRBS_ENABLE": "PRBS test enable",
    "WB_REG_INV_DELTA_Q": "Q15.16 reciprocal lattice scale",
    "WB_REG_DELTA_ADC_Q": "Q15.16 lattice spacing in ADC counts",
    "WB_REG_COEFF0": "Polynomial coefficient c0",
    "WB_REG_COEFF1": "Polynomial coefficient c1",
    "WB_REG_COEFF2": "Polynomial coefficient c2",
    "WB_REG_COEFF3": "Polynomial coefficient c3",
    "WB_REG_ALPHA": "Soft weighting alpha",
    "WB_REG_KILL_THRESHOLD": "Safety kill threshold",
    "WB_REG_CLEAR_FAULTS": "Pulse clear for sticky faults",
    "WB_REG_TELEM_CTRL": "Telemetry control bits",
    "WB_REG_TELEM_WINDOW": "Telemetry measurement window in cycles",
    "WB_REG_TELEM_STATUS": "Telemetry sample active/done status",
    "WB_REG_TELEM_FLIPS_DELTA": "Windowed syndrome flip count",
    "WB_REG_TELEM_TOTAL_FLIPS": "Saturating total syndrome flip count",
    "WB_REG_HEALTH_STATUS": "Health monitor compact status bitfield",
    "WB_REG_HEALTH_SAFETY_TRIPS": "Saturating count of safety trip events",
    "WB_REG_HEALTH_AXIS_STALLS": "Saturating count of AXI-Stream stall cycles",
    "WB_REG_HEALTH_DEC_VALID": "Saturating count of decoder valid cycles",
    "WB_REG_HEALTH_TELEM_DONE": (
        "Saturating count of completed telemetry windows"
    ),
    "WB_REG_CFG_APPLY": (
        "Commit staged config registers to active fabric config"
    ),
}

ACCESS: Dict[str, str] = {
    "WB_REG_BUILD_ID": "R",
    "WB_REG_STATUS": "R",
    "WB_REG_FAULT_FLAGS": "R",
    "WB_REG_TELEM_STATUS": "R",
    "WB_REG_TELEM_FLIPS_DELTA": "R",
    "WB_REG_TELEM_TOTAL_FLIPS": "R",
    "WB_REG_CLEAR_FAULTS": "W",
    "WB_REG_HEALTH_STATUS": "R",
    "WB_REG_HEALTH_SAFETY_TRIPS": "R",
    "WB_REG_HEALTH_AXIS_STALLS": "R",
    "WB_REG_HEALTH_DEC_VALID": "R",
    "WB_REG_HEALTH_TELEM_DONE": "R",
    "WB_REG_CFG_APPLY": "W",
}


def classify(name: str) -> str:
    low = name.lower()
    if any(
        k in low
        for k in [
            "status",
            "count",
            "state",
            "locked",
            "align",
            "fault",
            "flips",
            "total",
        ]
    ):
        return "fabric_to_axi_status"
    if any(
        k in low
        for k in [
            "ctrl",
            "enable",
            "config",
            "mode",
            "clear",
            "trigger",
            "alpha",
            "delta",
            "coeff",
            "threshold",
            "window",
        ]
    ):
        return "axi_to_fabric_control"
    return "unknown"


def read_registers() -> List[dict]:
    if not HEADER.exists():
        raise FileNotFoundError(f"Missing register header: {HEADER}")
    regs = []
    seen_addresses: Dict[int, str] = {}
    issues = []
    for line_no, line in enumerate(HEADER.read_text().splitlines(), start=1):
        m = DEFINE_RE.match(line)
        if not m:
            continue
        name, raw_addr = m.groups()
        address = int(raw_addr, 0)
        if address % 4 != 0:
            issues.append(
                (
                    f"line {line_no}: {name} address "
                    f"0x{address:02X} is not 32-bit aligned"
                )
            )
        if address in seen_addresses:
            issues.append(
                (
                    f"line {line_no}: {name} duplicates address "
                    f"0x{address:02X} used by {seen_addresses[address]}"
                )
            )
        seen_addresses[address] = name
        access = ACCESS.get(name, "R/W")
        regs.append(
            {
                "name": name.replace("WB_REG_", ""),
                "macro": name,
                "address": f"0x{address:02X}",
                "address_int": address,
                "access": access,
                "description": DESC.get(name, "TBD"),
                "cdc_class": classify(name),
            }
        )
    regs.sort(key=lambda r: r["address_int"])
    # Check monotonic 4-byte spacing only as informational, not fatal.
    for a, b in zip(regs, regs[1:]):
        if int(b["address_int"]) <= int(a["address_int"]):
            issues.append(
                f"non-monotonic register order: {a['macro']} then {b['macro']}"
            )
    OUT_LOG.write_text(
        "\n".join(issues) + ("\n" if issues else "No issues detected.\n")
    )
    return regs


def write_outputs(regs: List[dict]) -> None:
    OUT_JSON.write_text(json.dumps(regs, indent=2) + "\n")
    lines = [
        "# Extracted Register Map",
        "",
        "Generated from `firmware/registers.h`.",
        "",
        "| Address | Name | Access | CDC Class | Description |",
        "|---:|---|---|---|---|",
    ]
    for r in regs:
        lines.append(
            (
                f"| {r['address']} | {r['name']} | {r['access']} | "
                f"{r['cdc_class']} | {r['description']} |"
            )
        )
    lines.append("")
    lines.append("See `register_map_issues.log` for extraction warnings.")
    OUT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    regs = read_registers()
    write_outputs(regs)
    print(f"Extracted {len(regs)} registers")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    print(f"Wrote {OUT_LOG.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
