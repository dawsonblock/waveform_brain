# Compact Source Package v0.13

This package removes generated artifacts from the ZIP and keeps only reproducible source files.

## Removed from source archive

- `rtl/reciprocal_lut_w16_q24w25.mem`
- `register_map.json`
- `register_map.md`
- `register_map_issues.log`
- `cdc_crossing_suggestions.json`
- `cdc_crossing_suggestions.md`
- `sim/gkp_cosim_vectors.hex`
- `reports/`
- `build_dir/`
- `sim/build/`

## Regenerate when needed

```bash
make gen-lut
make extract-regs
make cdc-analyze
make cosim-vectors
```

The Vivado bitstream script now automatically runs:

```bash
python3 ../scripts/generate_reciprocal_lut.py
```

if the reciprocal LUT `.mem` file is missing.

The co-sim runner also generates the LUT if needed.

## Why this reduces build size

The reciprocal LUT has 131,072 text lines. It is deterministic and fully reproducible from `scripts/generate_reciprocal_lut.py`, so storing it in the source archive is unnecessary.

## Reproducibility rule

Generated files should not be committed or packaged unless a tool specifically needs them for an offline handoff. For normal development, regenerate them locally.
