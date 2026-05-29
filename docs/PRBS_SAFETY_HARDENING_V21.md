# PRBS And Safety Hardening (V21)

This version documents PRBS datapath integration and multi-channel safety
monitoring.

## Scope

- Route PRBS output into effective ADC datapath muxing.
- Expand safety monitoring to all four channels.
- Aggregate channel faults into a global safety kill signal.
- Expose per-channel fault flags in the low nibble of FAULT_FLAGS.

## Datapath Behavior

- `prbs_enable=0`: decoder and safety consume external ADC samples.
- `prbs_enable=1`: decoder and safety consume PRBS-derived samples.
- Decoder valid gating still respects aggregate safety kill.

## Safety Behavior

- Four independent safety monitor instances run in parallel.
- `safety_kill` asserts when any channel trips.
- `fault_flags[3:0]` correspond to channel fault latches.

## Validation Hooks

- Static checks confirm effective ADC mux and four-channel safety wiring.
- Safety behavioral simulation validates threshold edges, negative values,
  sticky fault latching, and clear behavior.

## Notes

V21 improves pre-board observability and deterministic bring-up, but board-ready
status still requires passing Vivado implementation gates and board smoke tests.
