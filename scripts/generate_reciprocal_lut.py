#!/usr/bin/env python3
"""
Generate reciprocal_lut_w16_q24w25.mem for soft_weighting.v.

Entry at denominator d:
    reciprocal[d] = round(2^RECIP_FRAC / d)

d=0 is defined as 0.

RECIP_WIDTH is RECIP_FRAC+1 so d=1 can represent exactly 2^RECIP_FRAC.
"""

from pathlib import Path

WIDTH = 16
DENOM_WIDTH = WIDTH + 1
RECIP_FRAC = 24
RECIP_WIDTH = RECIP_FRAC + 1
DEPTH = 1 << DENOM_WIDTH
OUT = Path(__file__).resolve().parents[1] / "rtl" / "reciprocal_lut_w16_q24w25.mem"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for d in range(DEPTH):
            if d == 0:
                value = 0
            else:
                value = ((1 << RECIP_FRAC) + (d // 2)) // d
                value = min((1 << RECIP_WIDTH) - 1, value)
            f.write(f"{value:07X}\n")
    print(f"Wrote {DEPTH} entries to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
