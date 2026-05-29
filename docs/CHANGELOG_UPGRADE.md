# Change Log — Upgraded Build

This document summarises the key improvements and fixes introduced in the upgraded Waveform Brain v1.0 build.

## Structural Improvements

- Added `rtl/axis_packet_fifo.v` and `rtl/axis_skid_buffer.v` (simulation-only; not instantiated in deployed hardware design).
- Inserted `axis_packet_fifo` after `packer_axis` in `waveform_control_4q_top.v`.
- Upgraded packet metadata to format version `4'h2` with a 32-bit sequence counter in beat 1.
- Added `frame_drop_count`, `sequence_counter`, FIFO level, FIFO overflow, and FIFO stall diagnostics.
- Exposed streaming diagnostics through AXI-Lite registers `0x5C` through `0x6C`.
- Added CDC synchronization for new streaming diagnostics.
- Added `userspace/validate_packet_capture.py`.
- Added `formal/packer_axis_properties.sv`.
- Added `docs/STREAMING_ROBUSTNESS_V19.md`.

- Corrected `rtl/packer_axis.v` to hold AXI4-Stream `TVALID`, `TDATA`, and `TLAST` stable until `TREADY` accepts each beat.
- Added packet metadata format version `4'h1` and updated userspace parser validation.
- Repaired `firmware/registers.h` include guard so health monitor register definitions are inside the guard.
- Upgraded `firmware/calibration_fsm.c` with telemetry-window helpers and alpha grid-search tuning.
- Added `scripts/audit_rtl_arithmetic.py` and Makefile target `audit-arith` to detect runtime division/modulo risk in RTL.
- Added `docs/AXIS_CALIB_AUDIT_V18.md`.

- Corrected `scripts/waveform_brain_bitstream.tcl` to resolve paths relative to the script instead of assuming current working directory.
- Marked RTL `.v` files as SystemVerilog in Vivado because the design uses SystemVerilog constructs.
- Changed Vivado flow to run implementation through `route_design`, generate reports, run CDC/implementation gates, then write bitstream only after gates pass.
- Replaced active CDC XDC skew commands with a safer review-only CDC overlay.
- Cleaned Makefile target ordering and fixed malformed `size-report` / `cdc-signoff-package` target collision.
- Added `docs/VIVADO_FLOW_FIX_V17.md`.

- Corrected `scripts/preboard_check.py` ordering so compact-package tests run before generated heavy artifacts are created.
- Added generated-artifact cleanup at the start of `preboard_check.py`.
- Added `docs/PREBOARD_GATE_FIX_V16.md`.

- Added v0.15 pre-board proof gate:
  - `scripts/preboard_check.py`
  - `scripts/implementation_gate.py`
  - `scripts/package_vivado_signoff.py`
  - `docs/PREBOARD_GATE_V15.md`
  - `docs/BOARD_READY_TEMPLATE.md`
- Hardened `scripts/parse_cdc_report.py` to emit JSON summaries and fail on critical CDC patterns.
- Replaced `scripts/build_gate_cdc.tcl` with a stricter JSON-producing CDC gate.
- Updated Vivado bitstream script to generate timing, DRC, utilization, clock interaction, and implementation gate reports.
- Added Makefile targets:
  - `preboard-check`
  - `implementation-gate`
  - `vivado-signoff-package`

- Added centralized CDC wrapper `rtl/waveform_brain_cdc_wrapper.v`.
- Added preferred CDC-hardened integration top `rtl/waveform_brain_axi4lite_cdc_top.v` with separate AXI and fabric clocks.
- Added coherent multi-bit config transfer through `xpm_cdc_handshake`.
- Added command pulse transfers through `xpm_cdc_pulse`.
- Added fabric-to-AXI counter transfers through `xpm_cdc_gray`.
- Patched `axilite_regfile_full.v` to emit `cfg_update_pulse` for coherent config handshakes.
- Added `constraints/cdc_xpm_wrapper_constraints.xdc`.
- Updated CDC cell-matching gate to check the centralized CDC wrapper hierarchy.
- Updated bitstream flow to default to `waveform_brain_axi4lite_cdc_top` and set `CDC_VERIFY_FAIL_ON_ZERO=1`.
- Added `docs/CDC_HARDENING_V14.md`, `docs/PHASE1_SIGNOFF_SHEET.md`, and `scripts/package_cdc_signoff.py`.

- Reduced package size by removing generated reciprocal LUT `.mem`, register-map outputs, CDC suggestion outputs, and generated co-sim vectors from the archive.
- Updated Vivado bitstream script to auto-generate the reciprocal LUT before adding memory files.
- Updated co-sim runner to generate the reciprocal LUT when missing.
- Expanded `clean-generated` and added `size-report` Makefile target.
- Added `docs/COMPACT_PACKAGE_V13.md`.

- Added optional standards-oriented AXI4-Lite slave module `rtl/axilite_regfile_full.v`.
- Added optional integration wrapper `rtl/waveform_brain_axi4lite_full_top.v`.
- Added bit-for-bit GKP golden-to-RTL co-simulation harness:
  - `scripts/generate_gkp_cosim_vectors.py`
  - `scripts/run_gkp_cosim.py`
  - `sim/tb_gkp_decoder_cosim.sv`
- Corrected `rtl/poly_eval.v` pipeline alignment so Horner stages use the same delayed `x` sample.
- Added `docs/AXILITE_FULL_V12.md` and `docs/GKP_COSIM_V12.md`.
- Added `cosim-vectors` and `cosim-gkp` Makefile targets.

- Replaced simplified always-ready `axilite_regfile.v` behavior with a deterministic lightweight handshake model.
- Added one-cycle accept pulses for write/read address channels.
- Added explicit write response/read valid pulse generation.
- Converted `CLEAR_FAULTS` and telemetry command bits into pulse-style outputs.
- Added byte-enable handling through `WSTRB` for writable registers.
- Added `docs/AXILITE_HANDSHAKE_V11.md`.

- Hardened reciprocal LUT implementation to v0.10 using `RECIP_FRAC=24` and `RECIP_WIDTH=25`.
- Replaced `reciprocal_lut_w16_q24.mem` with `reciprocal_lut_w16_q24w25.mem` so denom=1 can represent exactly `2^24`.
- Updated `soft_weighting.v`, `generate_reciprocal_lut.py`, and `soft_weight_model.py` to match the Q24/W25 table.
- Added an edge-case unit test for `alpha=1, r=0` producing exactly Q8.8 full-scale weight `256`.
- Added `docs/RECIPROCAL_LUT_V10.md`.

- Replaced runtime division in `rtl/soft_weighting.v` with a divider-free reciprocal-ROM plus multiplier pipeline.
- Added `rtl/reciprocal_lut_w16_q24w25.mem` and `scripts/generate_reciprocal_lut.py`.
- Reworked `rtl/gkp_decoder.v` with explicit pipeline alignment for position, syndrome, polynomial output, and soft-weight output.
- Added `userspace/soft_weight_model.py` and fixed-point LUT soft-weight helper routines.
- Added `docs/TIMING_REFACTOR_V09.md`.
- Updated Vivado bitstream script to add `.mem` files.

- Added `rtl/health_monitor.v` with saturating counters for safety trips, AXI-Stream stalls, decoder-valid cycles, and completed telemetry windows.
- Added health monitor registers at `0x48` through `0x58`.
- Added `userspace/health_monitor.py` for formatting health register dumps.
- Added `docs/HEALTH_MONITOR.md` with bring-up interpretation rules.

- Hardened `parse_cdc_report.py` with structured rule detection, JSON summaries, Markdown summaries, strict mode, sample line contexts, and exit-code based failure.
- Hardened `build_gate_cdc.tcl` to generate full/critical CDC reports, parse both reports, write JSON/Markdown summaries, and run cell-matching verification.
- Updated `verify_cdc_constraints.tcl` with optional hard-fail behavior and a Markdown cell-matching summary.
- Added `cdc-gate-check` Makefile target for parsing existing Vivado CDC reports outside Vivado.

- Added `parse_cdc_report.py` with exit-code based CDC parsing and optional JSON summaries.
- Added `build_gate_cdc.tcl` to generate CDC reports, run the parser, and fail the build on critical CDC issues.
- Updated the Vivado bitstream script to source the CDC build gate after implementation.
- Added `docs/CDC_BUILD_GATE.md` documenting the automated CDC flow.

- Added a **pipelined soft weighting** module (`soft_weighting.v`) that inserts a register between the computation of the denominator and the division. This reduces combinational delay and is a step toward a LUT‑based implementation.
- Added **pipelined cubic polynomial evaluation** in `poly_eval.v` using Horner's method with three sequential stages.
- Introduced a **pipelined GKP decoder** (`gkp_decoder.v`) that separates lattice snapping, polynomial evaluation, soft weighting, and correction summation into four stages.
- Added a **four‑channel decoder wrapper** (`gkp_decoder_4q_wrapper.v`) to handle parallel decoding.
- Implemented a **simple safety monitor** (`safety_monitor.v`) with a sticky fault flag and a clear_faults control.
- Added a **packet packer** (`packer_axis.v`) as a placeholder for AXI4‑Stream integration.
- Added a **top‑level integration module** (`waveform_control_4q_top.v`) that wires together the decoders, safety monitor, PRBS generator, and packet packer.
- Added a **register file** (`axilite_regfile.v`) with build ID, status, fault flags, configuration registers, and a clear faults control.
- Added a **telemetry counter** (`telemetry_counter.v`) with **windowed measurement**.  Software can configure a measurement window (`TELEM_WINDOW`), pulse `TELEM_CTRL[0]` to start a sample, and read back the number of flips detected in that window (`TELEM_FLIPS_DELTA`).  A running total of flips is maintained and can be cleared via `TELEM_CTRL[1]`.  Status bits (`TELEM_STATUS`) indicate when a sample is active and when it has completed.
- Added **calibration FSM skeleton** (`firmware/calibration_fsm.c`) and a corresponding header file with register offsets.
- Added documentation: `BOARD_VERIFICATION_CHECKLIST.md`, `REGISTER_MAP.md`, `VALIDATION_PLAN.md`, and this change log.

## Bug Fixes and Clean‑Ups

- Fixed sequential dependency bug in the original decoder by separating multipliers and accumulators into pipeline stages.
- Added sign handling and saturation logic when combining the lattice position and weighted correction.
- Unified naming conventions and parameterised widths for scalability.
- Added default initial values for configuration registers.

## Known Limitations

- Historical note: soft-weighting hardware division was removed in v0.9 by the
  reciprocal ROM + multiplier pipeline. This limitation no longer applies.
- Historical note: AXI-Stream stall handling in `packer_axis.v` was fixed in
  v0.19. The current design holds `TVALID/TDATA/TLAST` stable under stall.
- The stream path now preserves `TVALID/TDATA/TLAST` stability under backpressure,
  but the full end-to-end decoder source path is still bounded-loss rather than
  lossless under sustained downstream stalls.
- The **calibration FSM** is a skeleton. It must be completed with real control logic tied to the specific optical experiment and hardware.
- The **register file** implements a minimal subset of AXI‑Lite functionality. A production design should include proper ready/valid handshaking and possibly bus protocol checks.

## Next Steps

- Implement the full calibration FSM state machine, including PRBS‑driven latency measurement, LO phase control, GKP scale search, and alpha tuning.
- Complete board-level smoke automation and integrate strict release evidence logs.
- Perform full RTL simulation and timing analysis on RFSoC‑specific constraints.
- Develop and integrate a DMA driver and host‑side software for real‑time data streaming and visualisation.
