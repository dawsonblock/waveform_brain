# CDC Verification Plan

This document defines the CDC review gate for Waveform Brain v1.0 before board-level testing.

## Purpose

Waveform Brain has at least two practical timing domains: AXI/control and fabric/sample processing. Any register crossing between those domains must either be moved into a dedicated CDC wrapper or constrained through a reviewed CDC overlay.

## Required Scripts

Run these before implementation review:

```bash
python3 scripts/extract_register_map.py
python3 scripts/analyze_cdc_crossings.py
```

Run this after Vivado implementation:

```tcl
report_cdc -details -file reports/cdc_full.rpt
report_cdc -severity {Critical Warning} -file reports/cdc_critical.rpt
report_clock_interaction -file reports/clock_interaction.rpt
source scripts/verify_cdc_constraints.tcl
```

## Required Outputs

The CDC review package must include:

- `register_map.json`
- `register_map.md`
- `register_map_issues.log`
- `cdc_crossing_suggestions.md`
- `reports/cdc_full.rpt`
- `reports/cdc_critical.rpt`
- `reports/clock_interaction.rpt`

## Pass Criteria

- `register_map_issues.log` has no duplicate addresses or unaligned addresses.
- `cdc_critical.rpt` has zero unreviewed critical CDC warnings.
- Every multi-bit control/config crossing has an explicit synchronization method.
- Every status/counter crossing has explicit synchronization.
- Gray-coded counters have `set_bus_skew` where appropriate.
- Every uncommented XDC wildcard matches at least one real cell.

## Fail Criteria

Stop before board testing if any of these occur:

- CDC path appears as unknown or unsafe in `report_cdc`.
- Any XDC wildcard silently matches zero cells.
- AXI-visible counters cross clock domains without synchronization.
- Safety kill logic crosses clock domains outside a reviewed path.
- Latency measurement crosses clock domains as raw binary without synchronization.

## Review Note

The register-aware overlay is a temporary safety net. Prefer moving future crossings into a dedicated CDC wrapper using Xilinx XPM CDC primitives, then constraining and reporting those wrapper instances explicitly.


## Automated Parser / Build Gate

Run `scripts/build_gate_cdc.tcl` after implementation to generate and parse CDC reports. The Python parser `scripts/parse_cdc_report.py` returns a non-zero exit code when critical patterns such as unconstrained CDC paths, unknown CDC structures, or missing bus skew are found. Archive both the text reports and JSON summaries before board bring-up.


## Hardened CDC Build Gate

Run the CDC build gate after implementation:

```tcl
set CDC_GATE_STRICT 0
set CDC_GATE_CELLCHECK 1
source scripts/build_gate_cdc.tcl
```

Required outputs:

- `reports/cdc_full.rpt`
- `reports/cdc_critical.rpt`
- `reports/clock_interaction.rpt`
- `reports/cdc_full_summary.json`
- `reports/cdc_critical_summary.json`
- `reports/cdc_full_summary.md`
- `reports/cdc_critical_summary.md`
- `reports/cdc_cell_match_summary.md`

Stop conditions:

- parser fails on critical CDC issue patterns
- critical CDC report contains unknown CDC structures
- unconstrained CDC paths exist and are not explained
- expected CDC wildcard patterns match zero cells after hierarchy is stable
