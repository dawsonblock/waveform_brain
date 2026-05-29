# Pre-Board Gate Correction v0.16

v0.15 added the local pre-board gate, but the first ordering had a practical bug:

1. `preboard_check.py` generated `rtl/reciprocal_lut_w16_q24w25.mem`.
2. It then ran the unit tests.
3. `tests/test_compact_package.py` correctly failed because generated heavyweight artifacts were present.

v0.16 fixes that order.

## Correct order

1. Clean generated artifacts.
2. Run unit/static tests while the source tree is compact.
3. Regenerate deterministic artifacts.
4. Run register extraction and CDC suggestion generation.
5. Run Icarus/Vivado simulation for release validation. Exploration-only runs
   may skip local Icarus execution when tools are unavailable.

## Result

`make preboard-check` now validates both requirements:

- The package remains compact as source.
- The generated LUT/vector/register artifacts are reproducible.

This still does not replace Vivado implementation gates.
