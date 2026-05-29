#!/usr/bin/env python3
"""
Generate deterministic GKP decoder co-simulation vectors.

Output format per line:
adc inv_delta_q delta_adc_q coeff0 coeff1 coeff2 coeff3
alpha expected_corr expected_syndrome

All fields are hexadecimal. Signed fields are two's-complement encoded.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def twos(value: int, bits: int) -> int:
    mask = (1 << bits) - 1
    return value & mask


def syndrome_for(adc: int, inv_delta_q: int) -> int:
    scaled_full = int(adc) * int(inv_delta_q)
    scaled = (scaled_full + 0x8000) >> 16
    return scaled & 0x3


def main() -> int:
    from userspace.golden_gkp_model import gkp_decode_fixed_soft_lut

    parser = argparse.ArgumentParser(
        description="Generate GKP RTL/golden co-sim vectors."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "sim" / "gkp_cosim_vectors.hex",
    )
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument(
        "--profile",
        choices=["default", "edge"],
        default="default",
        help="Vector profile: default mixed-random or directed edge cases.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    inv_delta_q = 0x00010000
    delta_adc_q = 0x00010000

    # Use a simple mostly-linear correction polynomial by default:
    # coeff0=0, coeff1=1.0, coeff2=0, coeff3=0 in Q15.16.
    coeffs = [0x00000000, 0x00010000, 0x00000000, 0x00000000]
    alpha_values = [16, 32, 64, 128, 256, 512, 1024]

    if args.profile == "edge":
        # Directed edge cases to stress saturation and sign boundaries.
        samples = [
            -32768,
            -32767,
            -30000,
            -16384,
            -4097,
            -4096,
            -1,
            0,
            1,
            4096,
            4097,
            16384,
            30000,
            32766,
            32767,
        ]
        if args.count > len(samples):
            while len(samples) < args.count:
                samples.append(samples[len(samples) % 15])
    else:
        samples = [
            -32768,
            -24000,
            -16384,
            -4096,
            -1,
            0,
            1,
            4096,
            12345,
            24000,
            32767,
        ]
        while len(samples) < args.count:
            samples.append(rng.randint(-30000, 30000))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        f.write(
            "# adc inv_delta_q delta_adc_q coeff0 coeff1 coeff2 coeff3 "
            "alpha expected_corr expected_syndrome\n"
        )
        for i, adc in enumerate(samples[: args.count]):
            alpha = alpha_values[i % len(alpha_values)]
            expected_corr = gkp_decode_fixed_soft_lut(
                adc, inv_delta_q, delta_adc_q, coeffs, alpha
            )
            expected_syn = syndrome_for(adc, inv_delta_q)
            fields = [
                f"{twos(adc, 16):04X}",
                f"{twos(inv_delta_q, 32):08X}",
                f"{twos(delta_adc_q, 32):08X}",
                f"{twos(coeffs[0], 32):08X}",
                f"{twos(coeffs[1], 32):08X}",
                f"{twos(coeffs[2], 32):08X}",
                f"{twos(coeffs[3], 32):08X}",
                f"{twos(alpha, 16):04X}",
                f"{twos(expected_corr, 16):04X}",
                f"{twos(expected_syn, 2):01X}",
            ]
            f.write(" ".join(fields) + "\n")

    print(f"Wrote {args.count} vectors to {args.out} (profile={args.profile})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
