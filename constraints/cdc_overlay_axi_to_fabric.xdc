# =============================================================================
# Waveform Brain v1.0 — Register-Aware CDC Overlay
# =============================================================================
# Purpose:
#   Constrain AXI <-> fabric clock-domain crossings that live outside a
#   centralized waveform_brain_cdc_wrapper.
#
# Use:
#   1. Run scripts/extract_register_map.py
#   2. Run scripts/analyze_cdc_crossings.py
#   3. Replace example hierarchical wildcards below with real paths from
#      elaboration/implementation.
#   4. Re-run report_cdc and verify that every added path is reported as a
#      constrained user path.
# =============================================================================

# ---- Clock period helpers ----------------------------------------------------
# These assume the project defines axi_lite_clk and fabric_clk. Rename as needed.
set t_axi    [get_property -min PERIOD [get_clocks axi_lite_clk]]
set t_fabric [get_property -min PERIOD [get_clocks fabric_clk]]
set t_axi_fab [expr {min($t_axi, $t_fabric)}]
set t_fab_axi [expr {min($t_fabric, $t_axi)}]

# =============================================================================
# AXI -> Fabric controls/configuration
# =============================================================================
# Examples: PRBS_ENABLE, INV_DELTA_Q, DELTA_ADC_Q, COEFF0..3, ALPHA,
# KILL_THRESHOLD, CLEAR_FAULTS, TELEM_CTRL, TELEM_WINDOW.
#
# Use xpm_cdc_single for single-bit controls/pulses.
# Use xpm_cdc_handshake for multi-bit configuration words.
# Add max-delay/bus-skew only to the synchronized path endpoints after you know
# the real hierarchy.

# Example single-bit control crossing:
# set_max_delay -datapath_only $t_axi_fab \
#   -from [get_cells -quiet -hier -filter {NAME =~ *axilite_regfile*reg_prbs_enable*}] \
#   -to   [get_cells -quiet -hier -filter {NAME =~ *u_prbs_enable_sync*syncstages_ff_reg*}]

# Example multi-bit config crossing:
# set_max_delay -datapath_only $t_axi_fab \
#   -from [get_cells -quiet -hier -filter {NAME =~ *axilite_regfile*reg_alpha*}] \
#   -to   [get_cells -quiet -hier -filter {NAME =~ *u_alpha_cfg_hs*dest_hsdata_ff_reg*}]
# set_bus_skew $t_axi_fab \
#   -from [get_cells -quiet -hier -filter {NAME =~ *axilite_regfile*reg_alpha*}] \
#   -to   [get_cells -quiet -hier -filter {NAME =~ *u_alpha_cfg_hs*dest_hsdata_ff_reg*}]

# =============================================================================
# Fabric -> AXI status/counter paths
# =============================================================================
# Examples: STATUS, FAULT_FLAGS, TELEM_STATUS, TELEM_FLIPS_DELTA,
# TELEM_TOTAL_FLIPS.
#
# Use xpm_cdc_single for single-bit status flags.
# Use xpm_cdc_gray for counters/state IDs where practical.
# Add set_bus_skew for gray-coded buses.

# Example gray-coded counter crossing:
# set_max_delay -datapath_only $t_fab_axi \
#   -from [get_cells -quiet -hier -filter {NAME =~ *telemetry_counter*gray_total_flips_reg*}] \
#   -to   [get_cells -quiet -hier -filter {NAME =~ *u_telem_total_gray_sync*dest_graysync_ff_reg*}]
# set_bus_skew $t_fab_axi \
#   -from [get_cells -quiet -hier -filter {NAME =~ *telemetry_counter*gray_total_flips_reg*}] \
#   -to   [get_cells -quiet -hier -filter {NAME =~ *u_telem_total_gray_sync*dest_graysync_ff_reg*}]

# =============================================================================
# Safety Kill Path
# =============================================================================
# Safety outputs should remain simple, synchronized, and reviewed manually.
# Only constrain here if the path is outside the dedicated CDC wrapper.

# Example:
# set_max_delay -datapath_only [expr {$t_fabric * 0.75}] \
#   -from [get_cells -quiet -hier -filter {NAME =~ *safety_monitor*fault_latched*}] \
#   -to   [get_cells -quiet -hier -filter {NAME =~ *safety_kill*}]

# =============================================================================
# Review requirement
# =============================================================================
# Every uncommented constraint must be verified with:
#   report_cdc -details -file reports/cdc_full.rpt
#   report_cdc -severity {Critical Warning} -file reports/cdc_critical.rpt
#   source scripts/verify_cdc_constraints.tcl
# =============================================================================
