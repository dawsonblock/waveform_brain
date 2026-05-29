# =============================================================================
# Waveform Brain v1.0 — Central CDC Wrapper Review Overlay
# =============================================================================
# Use with waveform_brain_axi4lite_cdc_top.v and waveform_brain_cdc_wrapper.v.
#
# XPM_CDC primitives carry most of the structural CDC intent. This file avoids
# broad global timing waivers or broad asynchronous clock-group waivers so report_cdc
# can still detect unsafe paths.
#
# Board-specific clock definitions are intentionally not supplied here because
# they depend on the ZCU208/RFDC integration project. Add them in a board XDC.
# =============================================================================

# Required review commands after implementation:
#   report_cdc -details -file reports/cdc_full.rpt
#   report_cdc -severity {Critical Warning} -file reports/cdc_critical.rpt
#   report_clock_interaction -file reports/clock_interaction.rpt
#
# Required gate:
#   set CDC_GATE_CELLCHECK 1
#   set CDC_VERIFY_FAIL_ON_ZERO 1
#   source scripts/build_gate_cdc.tcl
#
# Do not add broad global false paths here. If a non-XPM CDC path remains,
# either move it into waveform_brain_cdc_wrapper.v or document a narrow,
# reviewed constraint with exact hierarchical endpoints.
