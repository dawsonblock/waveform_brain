# Pre-Board Gate v0.15

v0.15 adds proof gates that sit between source-code work and board flashing.

## New scripts

- `scripts/preboard_check.py`
- `scripts/implementation_gate.py`
- `scripts/package_vivado_signoff.py`

## Local pre-board check

Run:

```bash
make preboard-check
```

This performs all checks that do not require Vivado:

- regenerates reciprocal LUT
- generates co-sim vectors
- runs Python unit/static tests
- runs RTL sanity check
- extracts register map
- analyzes CDC crossing suggestions
- runs Icarus/Vivado simulation for release validation (optional only for exploration when tools are absent)

Outputs:

- `reports/preboard_local_summary.json`
- `reports/preboard_local_summary.md`

This check does not authorize board testing. It only confirms the source package is internally consistent.

## Vivado implementation gate

After implementation, the Vivado flow must produce:

- `reports/cdc_critical_summary.json`
- `reports/cdc_cell_match_summary.md`
- `reports/timing_summary.rpt`
- `reports/drc.rpt`

Then run:

```bash
python3 scripts/implementation_gate.py
```

Outputs:

- `reports/implementation_gate_summary.json`
- `reports/implementation_gate_summary.md`

## Report package

After the implementation gate passes, package evidence:

```bash
make vivado-signoff-package
```

Output:

- `reports/vivado_signoff_package.zip`

## Board-ready decision

Fill out:

- `docs/BOARD_READY_TEMPLATE.md`
- `docs/PHASE1_SIGNOFF_SHEET.md`

Do not flash the board unless the local pre-board check, CDC gate, timing gate, DRC gate, and sign-off sheet are complete.
