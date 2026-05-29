"""
Helpers for staged AXI-Lite configuration followed by one atomic commit.

The register map now stages config fields and applies them to the active fabric
configuration only when WB_REG_CFG_APPLY bit0 is written.
"""

from __future__ import annotations

from typing import Callable

# Byte offsets, mirrored from firmware/registers.h.
WB_REG_PRBS_ENABLE = 0x0C
WB_REG_INV_DELTA_Q = 0x10
WB_REG_DELTA_ADC_Q = 0x14
WB_REG_COEFF0 = 0x18
WB_REG_COEFF1 = 0x1C
WB_REG_COEFF2 = 0x20
WB_REG_COEFF3 = 0x24
WB_REG_ALPHA = 0x28
WB_REG_KILL_THRESHOLD = 0x2C
WB_REG_TELEM_WINDOW = 0x38
WB_REG_CFG_APPLY = 0x70

WB_CFG_APPLY_COMMIT = 0x1


def apply_staged_config(
    write32: Callable[[int, int], None],
    *,
    prbs_enable: int | None = None,
    inv_delta_q: int | None = None,
    delta_adc_q: int | None = None,
    coeff0: int | None = None,
    coeff1: int | None = None,
    coeff2: int | None = None,
    coeff3: int | None = None,
    alpha: int | None = None,
    kill_threshold: int | None = None,
    telem_window: int | None = None,
    commit: bool = True,
) -> None:
    """Stage any provided config values, then commit once if requested."""
    ordered_fields = [
        (WB_REG_PRBS_ENABLE, prbs_enable),
        (WB_REG_INV_DELTA_Q, inv_delta_q),
        (WB_REG_DELTA_ADC_Q, delta_adc_q),
        (WB_REG_COEFF0, coeff0),
        (WB_REG_COEFF1, coeff1),
        (WB_REG_COEFF2, coeff2),
        (WB_REG_COEFF3, coeff3),
        (WB_REG_ALPHA, alpha),
        (WB_REG_KILL_THRESHOLD, kill_threshold),
        (WB_REG_TELEM_WINDOW, telem_window),
    ]

    for offset, value in ordered_fields:
        if value is not None:
            write32(offset, int(value) & 0xFFFFFFFF)

    if commit:
        write32(WB_REG_CFG_APPLY, WB_CFG_APPLY_COMMIT)
