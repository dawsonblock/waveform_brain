# =============================================================================
# Waveform Brain v1.0 — CDC Constraint Verification Script
# =============================================================================
# Checks that the centralized CDC wrapper hierarchy exists after implementation.
#
# Usage:
#   set CDC_VERIFY_FAIL_ON_ZERO 1
#   source scripts/verify_cdc_constraints.tcl
# =============================================================================

puts "\n=== Waveform Brain v1.0 — CDC Constraint Verification ===\n"

if {![info exists CDC_VERIFY_FAIL_ON_ZERO]} {
    set CDC_VERIFY_FAIL_ON_ZERO 0
}

set cdc_patterns {
    {Central CDC Wrapper              *u_cdc*}
    {Config Handshake                 *u_cdc/u_cfg_hs*}
    {Clear Fault Pulse CDC            *u_cdc/u_clear_faults_pulse*}
    {Telemetry Start Pulse CDC        *u_cdc/u_telem_start_pulse*}
    {Telemetry Clear Pulse CDC        *u_cdc/u_telem_clear_pulse*}
    {Safety Kill Single CDC           *u_cdc/u_safety_kill_single*}
    {Telemetry Active Single CDC      *u_cdc/u_telem_active_single*}
    {Telemetry Done Pulse CDC         *u_cdc/u_telem_done_pulse*}
    {Fault Flags Array CDC            *u_cdc/u_fault_flags_array*}
    {Status Word Array CDC            *u_cdc/u_status_word_array*}
    {Health Status Array CDC          *u_cdc/u_health_status_array*}
    {Telemetry Delta Gray CDC         *u_cdc/u_telem_flips_delta_gray*}
    {Telemetry Total Gray CDC         *u_cdc/u_telem_total_flips_gray*}
    {Health Safety Trip Gray CDC      *u_cdc/u_health_safety_trip_gray*}
    {Health AXIS Stall Gray CDC       *u_cdc/u_health_axis_stall_gray*}
    {Health Decoder Valid Gray CDC    *u_cdc/u_health_decoder_valid_gray*}
    {Health Telemetry Done Gray CDC   *u_cdc/u_health_telem_done_gray*}
    {AXIS FIFO Level Array CDC      *u_cdc/u_axis_fifo_level_array*}
    {AXIS FIFO Overflow Gray CDC    *u_cdc/u_axis_fifo_overflow_gray*}
    {AXIS FIFO Stall Gray CDC       *u_cdc/u_axis_fifo_stall_gray*}
    {AXIS Frame Drop Gray CDC       *u_cdc/u_axis_frame_drop_gray*}
    {AXIS Sequence Gray CDC         *u_cdc/u_axis_sequence_gray*}
}

set total_patterns 0
set failed_patterns 0
set summary_lines {}

puts "Checking CDC wrapper cell matching...\n"
foreach item $cdc_patterns {
    set label   [lindex $item 0]
    set pattern [lindex $item 1]
    incr total_patterns
    set cells [get_cells -quiet -hierarchical -filter "NAME =~ $pattern"]
    set count [llength $cells]
    if {$count == 0} {
        puts [format "  %-35s : WARNING — 0 cells matched" $label]
        lappend summary_lines [format "%s | 0 | %s" $label $pattern]
        incr failed_patterns
    } else {
        puts [format "  %-35s : %d cells matched" $label $count]
        lappend summary_lines [format "%s | %d | %s" $label $count $pattern]
    }
}

puts "\n=== Summary ==="
puts "Patterns checked        : $total_patterns"
puts "Patterns with 0 matches : $failed_patterns"

file mkdir reports
set fp [open "reports/cdc_cell_match_summary.md" "w"]
puts $fp "# CDC Cell-Matching Summary\n"
puts $fp "| Pattern | Matches | Wildcard |"
puts $fp "|---|---:|---|"
foreach line $summary_lines {
    set parts [split $line "|"]
    puts $fp "| [string trim [lindex $parts 0]] | [string trim [lindex $parts 1]] | `[string trim [lindex $parts 2]]` |"
}
close $fp
puts "Wrote reports/cdc_cell_match_summary.md"

if {$failed_patterns > 0} {
    puts "\nACTION REQUIRED: Some CDC wrapper patterns did not match any cells."
    if {$CDC_VERIFY_FAIL_ON_ZERO} {
        puts "\n*** CDC CELL MATCH GATE FAILED ***"
        exit 1
    }
} else {
    puts "\nAll centralized CDC wrapper patterns matched cells successfully."
}

puts "\n=== CDC Report Summary ==="
catch { report_cdc -summary }

puts "\n=== Verification Complete ===\n"
