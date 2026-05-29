"""
Fixed-point soft-weighting reference helpers.

Matches rtl/soft_weighting.v default configuration:
    WIDTH=16, OUT_FRAC=8, RECIP_FRAC=24, RECIP_WIDTH=25
"""

from __future__ import annotations

WIDTH = 16
OUT_FRAC = 8
RECIP_FRAC = 24
RECIP_WIDTH = RECIP_FRAC + 1


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def abs_signed16_as_u17(value: int) -> int:
    value = signed16(value)
    if value < 0:
        return (-value) & 0x1FFFF
    return value & 0x1FFFF


def reciprocal_q24w25(denom: int) -> int:
    if denom <= 0:
        return 0
    value = ((1 << RECIP_FRAC) + (denom // 2)) // denom
    return min((1 << RECIP_WIDTH) - 1, value)


def soft_weight_lut(alpha: int, r_in: int) -> int:
    """Return Q8.8 weight matching the LUT reciprocal pipeline."""
    alpha &= 0xFFFF
    abs_r = abs_signed16_as_u17(r_in)
    denom = alpha + abs_r
    recip = reciprocal_q24w25(denom)
    product = alpha * recip
    return min(0xFFFF, (product + (1 << (RECIP_FRAC - OUT_FRAC - 1))) >> (RECIP_FRAC - OUT_FRAC))


def soft_weight_div_reference(alpha: int, r_in: int) -> int:
    """Exact integer division reference: round((alpha << OUT_FRAC) / (alpha + abs(r)))."""
    alpha &= 0xFFFF
    abs_r = abs_signed16_as_u17(r_in)
    denom = alpha + abs_r
    if denom == 0:
        return 0
    return (((alpha << OUT_FRAC) + (denom // 2)) // denom) & 0xFFFF
