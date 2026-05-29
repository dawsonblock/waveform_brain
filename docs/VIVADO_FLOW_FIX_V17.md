# Vivado Flow Correction v0.17

v0.17 fixes integration issues found after the v0.16 package.

## Corrections

### 1. Script-relative paths

`scripts/waveform_brain_bitstream.tcl` no longer assumes the current working
directory. It resolves:

- `script_dir`
- `project_root`
- `build_dir`
- `report_dir`

This makes the command below valid from the project root:

```bash
vivado -mode batch -source scripts/waveform_brain_bitstream.tcl
```

### 2. SystemVerilog file type

The RTL uses SystemVerilog constructs (`logic`, unpacked arrays, array ports),
but the files use `.v` extensions. The Vivado script now applies:

```tcl
set_property file_type SystemVerilog [get_files $rtl_files]
```

Without this, Vivado can parse the files as Verilog and fail.

### 3. Route before gates

The Vivado flow now runs implementation through `route_design`, opens the
implemented run, generates reports, then runs the CDC and implementation gates
before writing the bitstream.

### 4. Report generation before bitstream

The script now produces:

- `reports/timing_summary.rpt`
- `reports/drc.rpt`
- `reports/utilization.rpt`
- `reports/clock_interaction.rpt`
- CDC reports through `scripts/build_gate_cdc.tcl`

Then it runs:

```bash
python3 scripts/implementation_gate.py
```

The bitstream is written only if the gate passes.

### 5. Safer CDC XDC overlay

`constraints/cdc_xpm_wrapper_constraints.xdc` is now a review overlay only. It
does not contain broad false paths or invalid self-referential skew constraints.

### 6. Makefile cleanup

`make validate` now starts with `clean-generated`, then runs tests before
regenerating LUT/register/CDC artifacts. This avoids compact-package test
failures.

## Remaining requirement

This still needs a real Vivado run. The package is corrected for flow structure,
but it is not board-cleared until Vivado CDC/timing/DRC evidence exists.
