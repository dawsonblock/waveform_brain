# =============================================================================
# Waveform Brain v1.0 — CDC Build Gate
# =============================================================================
# Generates CDC reports, parses them into JSON, and optionally runs cell matching.
#
# Expected caller:
#   source scripts/build_gate_cdc.tcl
#
# Strictness knobs:
#   set CDC_GATE_STRICT 1          ;# fail on full-report critical patterns too
#   set CDC_GATE_CELLCHECK 1       ;# run verify_cdc_constraints.tcl
#   set CDC_VERIFY_FAIL_ON_ZERO 1  ;# fail if required CDC patterns match zero cells
# =============================================================================

puts "\n=== Running CDC Build Gate ===\n"

if {![info exists CDC_GATE_STRICT]} {
    set CDC_GATE_STRICT 0
}
if {![info exists CDC_GATE_CELLCHECK]} {
    set CDC_GATE_CELLCHECK 1
}
if {![info exists CDC_VERIFY_FAIL_ON_ZERO]} {
    set CDC_VERIFY_FAIL_ON_ZERO 1
}

set REPORT_DIR        "reports"
set CDC_FULL_REPORT   "$REPORT_DIR/cdc_full.rpt"
set CDC_CRIT_REPORT   "$REPORT_DIR/cdc_critical.rpt"
set CDC_FULL_JSON     "$REPORT_DIR/cdc_full_summary.json"
set CDC_CRIT_JSON     "$REPORT_DIR/cdc_critical_summary.json"
set PYTHON_PARSER     "scripts/parse_cdc_report.py"

file mkdir $REPORT_DIR

puts "Generating CDC reports..."
report_cdc -details                     -file $CDC_FULL_REPORT
report_cdc -severity {Critical Warning} -file $CDC_CRIT_REPORT

puts "Parsing critical CDC report..."
set crit_rc [catch {exec python3 $PYTHON_PARSER $CDC_CRIT_REPORT --json-out $CDC_CRIT_JSON --fail-on-critical} crit_out]
puts $crit_out

puts "Parsing full CDC report..."
if {$CDC_GATE_STRICT} {
    set full_rc [catch {exec python3 $PYTHON_PARSER $CDC_FULL_REPORT --json-out $CDC_FULL_JSON --fail-on-critical} full_out]
} else {
    set full_rc [catch {exec python3 $PYTHON_PARSER $CDC_FULL_REPORT --json-out $CDC_FULL_JSON} full_out]
}
puts $full_out

if {$CDC_GATE_CELLCHECK} {
    puts "Running CDC cell-match verification..."
    source scripts/verify_cdc_constraints.tcl
}

if {$crit_rc != 0 || ($CDC_GATE_STRICT && $full_rc != 0)} {
    puts "\n*** CDC BUILD GATE FAILED ***"
    puts "Review $CDC_CRIT_REPORT, $CDC_FULL_REPORT, and JSON summaries."
    exit 1
}

puts "\n*** CDC BUILD GATE PASSED ***\n"
