# Phase 0 Baseline Snapshot (repair/proof-hardening-v22)

Timestamp UTC: 2026-05-29

## Commands and observed baseline behavior

1. `python3 -m compileall -q userspace scripts tests firmware`
- Result: pass

2. `python3 scripts/rtl_sanity_check.py`
- Result: pass (non-fatal warning still present)
- Warning observed: `waveform_brain_cdc_wrapper.v: always_ff without explicit reset condition`

3. `python3 scripts/implementation_gate.py`
- Result: fail (expected fail-closed)
- Missing reports:
  - `reports/cdc_critical_summary.json`
  - `reports/cdc_cell_match_summary.md`
  - `reports/timing_summary.rpt`
  - `reports/drc.rpt`

4. `python3 scripts/check_release_prereqs.py`
- Result: fail (expected fail-closed)
- Missing Vivado/board-report artifacts:
  - `reports/cdc_critical_summary.json`
  - `reports/cdc_cell_match_summary.md`
  - `reports/timing_summary.rpt`
  - `reports/drc.rpt`
  - `reports/cdc_full.rpt`
  - `reports/cdc_critical.rpt`
  - `reports/clock_interaction.rpt`
  - `reports/utilization.rpt`
  - `reports/vivado_synth.log`
  - `reports/vivado_impl.log`

This baseline establishes that board-level gates fail closed before proof-hardening updates.
