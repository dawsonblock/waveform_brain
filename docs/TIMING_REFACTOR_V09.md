# Timing Refactor v0.9 — Divider-Free Soft Weighting

The previous `soft_weighting.v` used a runtime integer division:

```verilog
weight <= (alpha << 8) / denom;
```

That is a major timing risk in FPGA fabric. v0.9 replaces the datapath divider
with a precomputed reciprocal ROM and DSP-friendly multiply.

## Runtime equation

The target weight is:

```text
weight = alpha / (alpha + abs(r))
```

The hardware emits a Q8.8 integer approximation:

```text
weight_q8_8 ≈ alpha * round(2^24 / denom), stored in 25 bits >> 8
denom = alpha + abs(r)
```

## Files

- `rtl/soft_weighting.v`
- `rtl/reciprocal_lut_w16_q24w25.mem`
- `scripts/generate_reciprocal_lut.py`
- `userspace/soft_weight_model.py`

## Pipeline

`soft_weighting.v` now has three deterministic runtime stages:

1. absolute value and denominator
2. reciprocal ROM lookup
3. DSP multiply and Q8.8 output scaling

There is no `/` operator in the runtime datapath.

## Regenerating the ROM

```bash
python3 scripts/generate_reciprocal_lut.py
```

or:

```bash
make gen-lut
```

## Vivado note

The bitstream script now adds `.mem` files from `rtl/` so Vivado can initialize
the reciprocal ROM.

## Remaining proof gate

This is still not timing-proven. The next gate is Vivado synthesis and timing
analysis. The expected improvement is architectural: the critical arithmetic is
now a ROM lookup plus a multiplier instead of a divider.
