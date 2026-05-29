#!/usr/bin/env python3
"""
Waveform Brain v1.0 — CDC Crossing Analyzer

Reads register_map.json and emits a prioritized CDC review list.
The analyzer is register-aware only; it does not replace Vivado
`report_cdc`. Use it to decide which AXI<->fabric crossings need
explicit wrappers, XPM primitives, and overlay constraints.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER_JSON = ROOT / "register_map.json"
OUT_MD = ROOT / "cdc_crossing_suggestions.md"
OUT_JSON = ROOT / "cdc_crossing_suggestions.json"

CONTROL_KEYWORDS = [
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
STATUS_KEYWORDS = [
    "status",
    "count",
    "state",
    "locked",
    "align",
    "fault",
    "flips",
    "total",
    "done",
    "active",
]

SPECIAL_FAB_TO_AXI_RECOMMENDATIONS = {
    "telem_flips_delta": (
        "xpm_cdc_handshake for coherent window payload transfer; "
        "tie event pulse to payload delivery"
    ),
    "telem_total_flips": (
        "xpm_cdc_handshake for coherent window payload transfer; "
        "tie event pulse to payload delivery"
    ),
}


def load_registers(path: Path):
    with open(path) as f:
        return json.load(f)


def suggest_cdc_constraints(registers):
    suggestions = []
    for reg in registers:
        name = reg["name"].lower()
        address = reg.get("address", "TBD")
        access = reg.get("access", "R/W")
        is_control_name = any(kw in name for kw in CONTROL_KEYWORDS)
        is_status_name = any(kw in name for kw in STATUS_KEYWORDS)
        # Prefer access direction over keyword heuristics when available.
        if access in ("W", "R/W") and is_control_name:
            suggestions.append({
                "register": reg["name"],
                "address": address,
                "direction": "AXI -> Fabric",
                "risk": "control/config crossing",
                "recommended": (
                    "xpm_cdc_single for single-bit pulses; "
                    "xpm_cdc_handshake for multi-bit config; "
                    "constrain synchronized endpoints"
                ),
            })
        if access in ("R", "R/W") and is_status_name:
            # R/W controls with status-like names can be reviewed both ways.
            # Pure readback counters/status are the primary Fabric->AXI class.
            recommended = SPECIAL_FAB_TO_AXI_RECOMMENDATIONS.get(
                name,
                (
                    "xpm_cdc_single for single-bit status; xpm_cdc_gray "
                    "for counters/FSM; add set_bus_skew for gray buses"
                ),
            )
            suggestions.append({
                "register": reg["name"],
                "address": address,
                "direction": "Fabric -> AXI",
                "risk": "status/counter crossing",
                "recommended": recommended,
            })
    return suggestions


def write_outputs(suggestions):
    OUT_JSON.write_text(json.dumps(suggestions, indent=2) + "\n")
    lines = [
        "# CDC Crossing Suggestions",
        "",
        (
            "Generated from `register_map.json`. "
            "Treat this as a review aid, not a timing sign-off."
        ),
        "",
        "| Register | Address | Direction | Risk | Recommendation |",
        "|---|---:|---|---|---|",
    ]
    for s in suggestions:
        lines.append(
            f"| {s['register']} | {s['address']} | {s['direction']} "
            f"| {s['risk']} | {s['recommended']} |"
        )
    lines.append("")
    lines.append(
        "After implementation, verify actual crossings with "
        "`report_cdc -details` and "
        "`scripts/verify_cdc_constraints.tcl`."
    )
    OUT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    if not REGISTER_JSON.exists():
        print(
            "register_map.json not found. "
            "Run scripts/extract_register_map.py first."
        )
        return 1
    regs = load_registers(REGISTER_JSON)
    suggestions = suggest_cdc_constraints(regs)
    write_outputs(suggestions)
    print("=== Suggested CDC Crossings ===")
    for s in suggestions:
        print(
            f"- {s['register']} ({s['address']}): "
            f"{s['direction']} -> {s['recommended']}"
        )
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
