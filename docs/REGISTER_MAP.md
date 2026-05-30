# Register Map

This document describes the AXI‑Lite register map for the Waveform Brain v1.0
controller. The registers are memory‑mapped to the base address defined in the
firmware (e.g. `0x4000_0000`). All offsets are in bytes.

- `0x00` `BUILD_ID` (`R`): 32‑bit ASCII identifier (`"WBV1"`).
- `0x04` `STATUS` (`R`): 16‑bit status word (kill flag and decoder-valid flags).
- `0x08` `FAULT_FLAGS` (`R`): 16‑bit latched fault flags (sticky until cleared).
- `0x0C` `PRBS_ENABLE` (`R/W`): bit0 enables PRBS test mode.
- `0x10` `INV_DELTA_Q` (`R/W`): 32‑bit Q15.16 reciprocal lattice spacing.
- `0x14` `DELTA_ADC_Q` (`R/W`): 32‑bit Q15.16 lattice spacing in ADC counts.
- `0x18` `COEFF0` (`R/W`): cubic polynomial coefficient `c0` (Q15.16).
- `0x1C` `COEFF1` (`R/W`): cubic polynomial coefficient `c1` (Q15.16).
- `0x20` `COEFF2` (`R/W`): cubic polynomial coefficient `c2` (Q15.16).
- `0x24` `COEFF3` (`R/W`): cubic polynomial coefficient `c3` (Q15.16).
- `0x28` `ALPHA` (`R/W`): 16‑bit soft-weighting parameter (unsigned).
- `0x2C` `KILL_THRESHOLD` (`R/W`): 16‑bit kill threshold for safety monitor.
- `0x30` `CLEAR_FAULTS` (`W`): write 1 to clear latched fault flags.
- `0x34` `TELEM_CTRL` (`R/W`): telemetry control (bit0 start, bit1 clear total).
- `0x38` `TELEM_WINDOW` (`R/W`): cycles per telemetry measurement window.
- `0x3C` `TELEM_STATUS` (`R`): bit0 sample_active, bit1 sample_done.
- `0x40` `TELEM_FLIPS_DELTA` (`R`): flips in last completed telemetry window.
- `0x44` `TELEM_TOTAL_FLIPS` (`R`): running total flips since last clear.

**Note:** The preferred path is `rtl/axilite_regfile_full.v`, which implements proper
AXI-Lite ready/valid handshaking and staged configuration registers. Runtime
configuration updates are committed atomically via `CFG_APPLY` at `0x70`.

## Health Monitor Registers

- `0x48` `HEALTH_STATUS` (`R`): compact health status bitfield.
- `0x4C` `HEALTH_SAFETY_TRIPS` (`R`): saturating count of safety trip events.
- `0x50` `HEALTH_AXIS_STALLS` (`R`): saturating AXI-Stream stall-cycle count.
- `0x54` `HEALTH_DEC_VALID` (`R`): saturating decoder-valid cycle count.
- `0x58` `HEALTH_TELEM_DONE` (`R`): saturating completed telemetry windows.
- `0x5C` `AXIS_FIFO_LEVEL` (`R`): current AXI packet FIFO fill level (beats).
- `0x60` `AXIS_FIFO_OVERFLOW` (`R`): saturating FIFO overflow count.
- `0x64` `AXIS_FIFO_STALLS` (`R`): saturating downstream stall-cycle count.
- `0x68` `AXIS_FRAME_DROPS` (`R`): saturating dropped-frame count.
- `0x6C` `AXIS_SEQUENCE` (`R`): running packet sequence counter.
- `0x70` `CFG_APPLY` (`W`): bit0 commits staged config with one CDC pulse.
