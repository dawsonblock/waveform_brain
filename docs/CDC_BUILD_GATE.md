# CDC Build Gate

Waveform Brain v1.0 includes a hardened CDC build gate for Vivado reports.

## Files

- `scripts/parse_cdc_report.py`
- `scripts/build_gate_cdc.tcl`
- `scripts/verify_cdc_constraints.tcl`

## Parser

Use the parser after Vivado generates CDC reports:

```bash
python3 scripts/parse_cdc_report.py reports/cdc_full.rpt
python3 scripts/parse_cdc_report.py reports/cdc_critical.rpt
```

The parser returns a non-zero exit code when critical issue patterns are found.

It detects:

- unconstrained CDC paths
- unknown CDC structures
- missing `set_bus_skew`
- missing `ASYNC_REG` warnings

## JSON and Markdown outputs

```bash
python3 scripts/parse_cdc_report.py \
  reports/cdc_full.rpt \
  --json-out reports/cdc_full_summary.json \
  --md-out reports/cdc_full_summary.md
```

## Strict mode

Strict mode treats warnings as fatal:

```bash
python3 scripts/parse_cdc_report.py --strict reports/cdc_full.rpt
```

## Vivado build gate

In Vivado, after implementation:

```tcl
set CDC_GATE_STRICT 0
set CDC_GATE_CELLCHECK 1
source scripts/build_gate_cdc.tcl
```

The Tcl gate generates:

- `reports/cdc_full.rpt`
- `reports/cdc_critical.rpt`
- `reports/clock_interaction.rpt`
- `reports/cdc_full_summary.json`
- `reports/cdc_critical_summary.json`
- `reports/cdc_full_summary.md`
- `reports/cdc_critical_summary.md`

It aborts the build when the parser finds critical CDC issue patterns.

## Cell matching

`verify_cdc_constraints.tcl` checks whether important wildcard patterns actually match cells.

Optional hard fail:

```tcl
set CDC_VERIFY_FAIL_ON_ZERO 1
source scripts/verify_cdc_constraints.tcl
```

For early scaffold work, leave this disabled until hierarchy is stable.

## Phase gate

Before board-level verification, archive:

- CDC reports
- JSON summaries
- Markdown summaries
- cell-matching summary
- clock interaction report

This still does not prove hardware behavior. It is a pre-hardware correctness gate.
