#!/usr/bin/env python3
"""
Waveform Brain v1.0 — Health Monitor Reader

Small host-side helper for reading health-monitor counters from a text dump,
mock register dictionary, or a future /dev/mem/UIO backend.

This scaffold intentionally avoids assuming a specific Linux driver. The
register constants match firmware/registers.h.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict


REG_HEALTH_STATUS = 0x48
REG_HEALTH_SAFETY_TRIPS = 0x4C
REG_HEALTH_AXIS_STALLS = 0x50
REG_HEALTH_DEC_VALID = 0x54
REG_HEALTH_TELEM_DONE = 0x58


@dataclass
class HealthSnapshot:
    status: int
    safety_trips: int
    axis_stalls: int
    decoder_valid_cycles: int
    telemetry_done_windows: int

    @property
    def safety_fault_latched(self) -> bool:
        return bool(self.status & (1 << 0))

    @property
    def safety_kill(self) -> bool:
        return bool(self.status & (1 << 1))

    @property
    def axis_backpressure_now(self) -> bool:
        return bool(self.status & (1 << 2))

    @property
    def any_decoder_valid(self) -> bool:
        return bool(self.status & (1 << 3))

    @property
    def telemetry_active(self) -> bool:
        return bool(self.status & (1 << 4))

    @property
    def telemetry_done(self) -> bool:
        return bool(self.status & (1 << 5))


def parse_register_dump(path: str) -> Dict[int, int]:
    """
    Parse lines like:
        0x48 0x00000001
        HEALTH_STATUS=0x00000001

    This is a convenience for offline bring-up logs.
    """
    regs: Dict[int, int] = {}
    name_to_addr = {
        "HEALTH_STATUS": REG_HEALTH_STATUS,
        "HEALTH_SAFETY_TRIPS": REG_HEALTH_SAFETY_TRIPS,
        "HEALTH_AXIS_STALLS": REG_HEALTH_AXIS_STALLS,
        "HEALTH_DEC_VALID": REG_HEALTH_DEC_VALID,
        "HEALTH_TELEM_DONE": REG_HEALTH_TELEM_DONE,
    }
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = int(value.strip(), 0)
                if key in name_to_addr:
                    regs[name_to_addr[key]] = value
                else:
                    regs[int(key, 0)] = value
            else:
                parts = line.split()
                if len(parts) >= 2:
                    regs[int(parts[0], 0)] = int(parts[1], 0)
    return regs


def snapshot_from_regs(regs: Dict[int, int]) -> HealthSnapshot:
    return HealthSnapshot(
        status=regs.get(REG_HEALTH_STATUS, 0),
        safety_trips=regs.get(REG_HEALTH_SAFETY_TRIPS, 0),
        axis_stalls=regs.get(REG_HEALTH_AXIS_STALLS, 0),
        decoder_valid_cycles=regs.get(REG_HEALTH_DEC_VALID, 0),
        telemetry_done_windows=regs.get(REG_HEALTH_TELEM_DONE, 0),
    )


def format_snapshot(s: HealthSnapshot) -> str:
    return "\n".join(
        [
            "=== Waveform Brain Health Snapshot ===",
            f"status                  : 0x{s.status:08X}",
            f"safety_fault_latched    : {s.safety_fault_latched}",
            f"safety_kill             : {s.safety_kill}",
            f"axis_backpressure_now   : {s.axis_backpressure_now}",
            f"any_decoder_valid       : {s.any_decoder_valid}",
            f"telemetry_active        : {s.telemetry_active}",
            f"telemetry_done          : {s.telemetry_done}",
            f"safety_trips            : {s.safety_trips}",
            f"axis_stall_cycles       : {s.axis_stalls}",
            f"decoder_valid_cycles    : {s.decoder_valid_cycles}",
            f"telemetry_done_windows  : {s.telemetry_done_windows}",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Read/format Waveform Brain health counters.")
    parser.add_argument("--dump", required=True, help="Text file containing register dump lines.")
    args = parser.parse_args()

    regs = parse_register_dump(args.dump)
    snap = snapshot_from_regs(regs)
    print(format_snapshot(snap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
