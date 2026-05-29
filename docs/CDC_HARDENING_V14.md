# Centralized CDC Hardening v0.14

v0.14 moves CDC handling from a mostly reactive overlay model to a centralized,
constrained-by-design structure.

## Added RTL

- `rtl/waveform_brain_cdc_wrapper.v`
- `rtl/waveform_brain_axi4lite_cdc_top.v`

## Design rule

All AXI clock to fabric clock crossings should pass through:

`waveform_brain_cdc_wrapper`

Do not directly connect AXI-Lite register outputs to fabric logic when the
clocks may differ.

## Crossing policy

| Signal class | Direction | Mechanism |
| --- | --- | --- |
| Coherent config bus | AXI to fabric | `xpm_cdc_handshake` |
| Command pulses | AXI to fabric | `xpm_cdc_pulse` |
| Safety kill | Fabric to AXI | `xpm_cdc_single` |
| Diagnostic bitfields | Fabric to AXI | `xpm_cdc_array_single` |
| Telemetry window payload/event | Fabric to AXI | `xpm_cdc_handshake` |
| Counters | Fabric to AXI | `xpm_cdc_gray` |

## Preferred integration top

Use:

`waveform_brain_axi4lite_cdc_top`

This top exposes separate clocks:

- `s_axi_aclk`
- `fabric_clk`

The Vivado bitstream script now defaults to this CDC-hardened top through:

```tcl
set WB_TOP waveform_brain_axi4lite_cdc_top
```

Override only when intentionally building a lower-level scaffold.

## Constraint files

Added:

`constraints/cdc_xpm_wrapper_constraints.xdc`

This file is a review overlay. XPM primitives are expected to be recognized by
Vivado `report_cdc`; the overlay focuses on named wrapper paths and gray-bus
skew review.

## Build gate

The bitstream script now sets:

```tcl
set CDC_GATE_CELLCHECK 1
set CDC_VERIFY_FAIL_ON_ZERO 1
```

That means the CDC wrapper hierarchy must be present after implementation or the
gate fails. This prevents silent wildcard failures.

## Stop condition

Do not proceed to board verification until:

- `reports/cdc_critical_summary.json` reports pass.
- `reports/cdc_full_summary.json` reports pass or every remaining item is explained.
- `reports/cdc_cell_match_summary.md` shows non-zero matches for every required wrapper pattern.
