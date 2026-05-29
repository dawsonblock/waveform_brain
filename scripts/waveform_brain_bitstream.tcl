# waveform_brain_bitstream.tcl
#
# Vivado build script for Waveform Brain.
#
# v0.17 corrections:
#   - Resolves paths relative to this script instead of assuming cwd.
#   - Marks RTL .v files as SystemVerilog because the RTL uses logic/arrays.
#   - Runs implementation only through route_design before sign-off gates.
#   - Generates timing/DRC/utilization/clock-interaction reports before bitstream.
#   - Runs CDC and implementation gates before writing the bitstream.

set script_dir   [file dirname [file normalize [info script]]]
set project_root [file dirname $script_dir]
set build_dir    [file join $project_root build_dir]
set report_dir   [file join $project_root reports]
set synth_log    [file join $report_dir vivado_synth.log]
set impl_log     [file join $report_dir vivado_impl.log]

cd $project_root

if {![info exists WB_PART]} {
    set WB_PART xczu48dr-2-ffvg1517
}
if {![info exists WB_TOP]} {
    set WB_TOP waveform_brain_axi4lite_cdc_top
}
if {![info exists WB_JOBS]} {
    set WB_JOBS 4
}

create_project waveform_brain_v1 $build_dir -part $WB_PART -force

set recip_mem [file join $project_root rtl reciprocal_lut_w16_q24w25.mem]
if {![file exists $recip_mem]} {
    puts "Generating reciprocal LUT memory file..."
    exec python3 [file join $project_root scripts generate_reciprocal_lut.py]
}

set rtl_files [glob -nocomplain [file join $project_root rtl *.v]]
if {[llength $rtl_files] == 0} {
    puts "*** ERROR: no RTL files found under $project_root/rtl"
    exit 1
}
add_files $rtl_files
set_property file_type SystemVerilog [get_files $rtl_files]

set mem_files [glob -nocomplain [file join $project_root rtl *.mem]]
if {[llength $mem_files] > 0} {
    add_files -norecurse $mem_files
}

set xdc_files [glob -nocomplain [file join $project_root constraints *.xdc]]
if {[llength $xdc_files] > 0} {
    add_files -fileset constrs_1 $xdc_files
}

set_property top $WB_TOP [current_fileset]
update_compile_order -fileset sources_1

# TODO before hardware use:
# - Add board-specific primary clocks and reset constraints.
# - Add RFDC IP configuration.
# - Add real IO/pin constraints.
# - Confirm generated clocks and clock names used in CDC reports.

file mkdir $report_dir

set synth_fp [open $synth_log "w"]
puts $synth_fp "Vivado synthesis stage"
puts $synth_fp "top=$WB_TOP"
puts $synth_fp "part=$WB_PART"
puts $synth_fp "status=running"
close $synth_fp

launch_runs synth_1 -jobs $WB_JOBS
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    set synth_fp [open $synth_log "a"]
    puts $synth_fp "status=failed"
    close $synth_fp
    puts "*** SYNTHESIS DID NOT COMPLETE ***"
    exit 1
}

set synth_fp [open $synth_log "a"]
puts $synth_fp "status=completed"
close $synth_fp

set impl_fp [open $impl_log "w"]
puts $impl_fp "Vivado implementation stage"
puts $impl_fp "top=$WB_TOP"
puts $impl_fp "part=$WB_PART"
puts $impl_fp "status=running"
close $impl_fp

launch_runs impl_1 -to_step route_design -jobs $WB_JOBS
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
    set impl_fp [open $impl_log "a"]
    puts $impl_fp "status=failed"
    close $impl_fp
    puts "*** IMPLEMENTATION DID NOT COMPLETE ***"
    exit 1
}

set impl_fp [open $impl_log "a"]
puts $impl_fp "status=completed"
close $impl_fp

open_run impl_1

report_timing_summary    -file [file join $report_dir timing_summary.rpt]
report_drc               -file [file join $report_dir drc.rpt]
report_utilization       -file [file join $report_dir utilization.rpt]
report_clock_interaction -file [file join $report_dir clock_interaction.rpt]

set CDC_GATE_STRICT 0
set CDC_GATE_CELLCHECK 1
set CDC_VERIFY_FAIL_ON_ZERO 1
source [file join $project_root scripts build_gate_cdc.tcl]

puts "Running implementation report gate..."
set impl_gate_rc [catch {exec python3 [file join $project_root scripts implementation_gate.py]} impl_gate_out]
puts $impl_gate_out
if {$impl_gate_rc != 0} {
    puts "*** IMPLEMENTATION GATE FAILED ***"
    exit 1
}

write_bitstream -force [file join $build_dir waveform_brain_v1.bit]
puts "Bitstream written to [file join $build_dir waveform_brain_v1.bit]"
