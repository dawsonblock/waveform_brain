# Board Ready Template

Project: Waveform Brain v1.0  
Target: ZCU208 / XCZU48DR RFSoC  
Selected top module: `waveform_brain_axi4lite_cdc_top`

## Status

| Gate | Pass | Evidence |
|---|---:|---|
| Local pre-board check |  | `reports/preboard_local_summary.md` |
| Vivado elaboration |  |  |
| CDC critical gate |  | `reports/cdc_critical_summary.json` |
| CDC cell match gate |  | `reports/cdc_cell_match_summary.md` |
| Clock interaction reviewed |  | `reports/clock_interaction.rpt` |
| Timing pass |  | `reports/timing_summary.rpt` |
| DRC pass |  | `reports/drc.rpt` |
| Utilization reviewed |  | `reports/utilization.rpt` |
| Reciprocal LUT generated |  | `rtl/reciprocal_lut_w16_q24w25.mem` |
| Co-sim pass or deferred |  | `reports/preboard_local_summary.md` |
| Phase 1 sign-off completed |  | `docs/PHASE1_SIGNOFF_SHEET.md` |

## Board testing decision

Board-level verification may proceed: `YES / NO`

Reviewer:  
Date:  
Notes:

## Stop condition

If any gate above is not passed or explicitly deferred with justification, do not flash the board.
