"""
golden_gkp_model.py

This module contains a reference implementation of the square‑lattice GKP
decoder. It can be used to generate golden data for validating the
hardware implementation. The functions here operate on Python integers
and floats and are not optimised for speed.

The model performs:

1. Lattice snapping: maps an input value `m` (in ADC counts) to the
   nearest lattice index `n` by multiplying with the reciprocal
   lattice spacing and rounding.
2. Remainder computation: `r = m - n * delta_adc`.
3. Polynomial correction: evaluates a cubic polynomial on `r` with
   provided coefficients.
4. Soft weighting: computes `w = alpha / (alpha + abs(r))` and applies it
   to the polynomial correction.

Usage:

```python
from golden_gkp_model import gkp_decode

adc_sample = 12345
inv_delta = 1.0 / 4096.0
delta_adc = 4096.0
coeffs = [0.0, 0.0, 0.0, 0.0]
alpha = 1.0

corr = gkp_decode(adc_sample, inv_delta, delta_adc, coeffs, alpha)
```
"""

from dataclasses import dataclass
from typing import List

from userspace.soft_weight_model import soft_weight_lut


def gkp_decode(m: float, inv_delta: float, delta_adc: float,
               coeffs: List[float], alpha: float) -> float:
    """Perform soft‑decision GKP decoding on a single measurement.

    :param m: Input measurement (ADC counts).
    :param inv_delta: Reciprocal of the lattice spacing.
    :param delta_adc: Lattice spacing in ADC counts.
    :param coeffs: List of 4 cubic polynomial coefficients [c0, c1, c2, c3].
    :param alpha: Soft weighting parameter.
    :return: Corrected output value.
    """
    # Lattice snapping
    n_hat = round(m * inv_delta)
    pos = n_hat * delta_adc
    r = m - pos
    # Polynomial correction
    # Evaluate c0 + c1 * r + c2 * r^2 + c3 * r^3
    poly = coeffs[0]
    poly += coeffs[1] * r
    poly += coeffs[2] * (r ** 2)
    poly += coeffs[3] * (r ** 3)
    # Soft weight
    w = alpha / (alpha + abs(r)) if alpha > 0 else 0.0
    corr = pos + poly * w
    return corr


if __name__ == "__main__":
    # Basic sanity test
    print(gkp_decode(10000.0, 1.0 / 4096.0, 4096.0, [0.0, 0.0, 0.0, 0.0], 1.0))

def gkp_decode_fixed_soft_lut(m: int, inv_delta_q: int, delta_adc_q: int, coeffs_q: List[int], alpha: int) -> int:
    """
    Integer-oriented scaffold reference for the divider-free soft weighting path.

    This is not a complete bit-accurate model of every RTL pipeline register,
    but it uses the same LUT reciprocal soft-weight formula as soft_weighting.v.
    """
    # Lattice snap using Q15.16 style scaling.
    scaled_full = int(m) * int(inv_delta_q)
    scaled = (scaled_full + 0x8000) >> 16
    rounded_n = scaled & 0xFFFF
    if rounded_n & 0x8000:
        rounded_n -= 0x10000

    pos = (rounded_n * int(delta_adc_q)) >> 16
    r = int(m) - pos

    # Basic polynomial model in Q15.16 Horner form.
    x = r
    c0, c1, c2, c3 = [int(c) for c in coeffs_q]
    y = (((c3 * x + 0x8000) >> 16) + c2)
    y = (((y * x + 0x8000) >> 16) + c1)
    y = (((y * x + 0x8000) >> 16) + c0)

    weight = soft_weight_lut(alpha, r)
    corr = pos + ((y * weight) >> 8)

    # Saturate to signed 16-bit.
    if corr > 32767:
        return 32767
    if corr < -32768:
        return -32768
    return corr
