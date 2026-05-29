#!/usr/bin/env python3
"""Board adapter contract for fail-closed smoke scaffolding."""

from __future__ import annotations

ADAPTER_CONTRACT_VERSION = 1

CHECK_REASON_CODES = {
    "read_build_id": "BUILD_ID_ADAPTER_NOT_IMPLEMENTED",
    "axi_lite_smoke": "AXI_LITE_ADAPTER_NOT_IMPLEMENTED",
    "config_apply_smoke": "CONFIG_APPLY_ADAPTER_NOT_IMPLEMENTED",
    "safety_trip_smoke": "SAFETY_ADAPTER_NOT_IMPLEMENTED",
    "prbs_capture_smoke": "PRBS_CAPTURE_ADAPTER_NOT_IMPLEMENTED",
    "axis_capture_smoke": "AXIS_CAPTURE_ADAPTER_NOT_IMPLEMENTED",
    "telemetry_window_smoke": "TELEMETRY_ADAPTER_NOT_IMPLEMENTED",
}

BOARD_CAPTURE_BLOCKED_CODE = "BOARD_CAPTURE_ADAPTER_NOT_IMPLEMENTED"


def code_for_check(check_name: str) -> str:
    return CHECK_REASON_CODES.get(check_name, "ADAPTER_NOT_IMPLEMENTED")
