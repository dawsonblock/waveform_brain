# Phase 1 CDC Sign-off Sheet

Project: Waveform Brain v1.0  
Target: ZCU208 / XCZU48DR RFSoC  
Scope: CDC and pre-board implementation sign-off

## Required reports

| Report | Present | Pass |
|---|---:|---:|
| `reports/cdc_full.rpt` |  |  |
| `reports/cdc_critical.rpt` |  |  |
| `reports/clock_interaction.rpt` |  |  |
| `reports/cdc_full_summary.json` |  |  |
| `reports/cdc_critical_summary.json` |  |  |
| `reports/cdc_cell_match_summary.md` |  |  |

## Pass criteria

- No critical CDC warnings.
- No unknown CDC structures unless explicitly justified.
- No unconstrained CDC paths unless explicitly justified.
- Every required centralized CDC wrapper pattern matches at least one cell.
- Multi-bit counters cross through `xpm_cdc_gray`.
- Multi-bit coherent config crosses through `xpm_cdc_handshake`.
- Command pulses cross through `xpm_cdc_pulse`.
- Safety kill readback crosses through `xpm_cdc_single`.
- No broad global `set_false_path` or broad asynchronous clock-group waiver is used to hide failures.

## Deferred or explained paths

Document any non-fixed path here.

| Path | Report location | Reason | Risk | Reviewer decision |
|---|---|---|---|---|
|  |  |  |  |  |

## Reviewer decision

Board-level verification may proceed: `YES / NO`

Reviewer:  
Date:  
Notes:
