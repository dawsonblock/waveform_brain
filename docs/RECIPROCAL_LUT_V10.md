# Reciprocal LUT Hardening v0.10

The conceptual LUT version is the right direction, but a Verilog function such as:

```verilog
return (65536 / d);
```

can still synthesize into divider-like logic if the tool does not treat it as a
constant ROM. v0.10 therefore uses a generated `.mem` file and `$readmemh`.

## Key hardening change

The reciprocal table now uses:

- `RECIP_FRAC = 24`
- `RECIP_WIDTH = 25`
- file: `rtl/reciprocal_lut_w16_q24w25.mem`

Why 25 bits?

For `denom = 1`, the exact reciprocal is:

```text
2^24 / 1 = 16,777,216 = 0x1000000
```

That value requires 25 bits. A 24-bit ROM would saturate it to `0xFFFFFF`,
causing the Q8.8 full-scale weight to under-report by one LSB in the edge case
`alpha=1, r=0`.

## Runtime datapath

The runtime datapath has no division:

```text
denom = alpha + abs(r)
recip = reciprocal_rom[denom]
weight_q8_8 = round((alpha * recip) >> (RECIP_FRAC - OUT_FRAC))
```

## Remaining proof gate

This is still not Vivado-proven. The next required checks are:

1. Vivado elaboration.
2. ROM inference report.
3. DSP inference report.
4. Timing summary.
5. CDC build gate.
6. PRBS/ILA board proof after timing/CDC pass.
