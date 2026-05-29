# Validation Plan

This document outlines a validation strategy for the Waveform Brain v1.0 controller. It focuses on verifying deterministic behavior, proper decoder function, safety interlocks, and streaming. It serves as a living checklist during development.

## Validation Flow Matrix

| Flow | Command | Simulation requirement | Vivado requirement |
| --- | --- | --- | --- |
| Exploration | `make validate` | Optional | Optional |
| Local proof | `make release-validate-local` | Mandatory | Not required |
| Board proof | `make release-validate-board` | Mandatory | Mandatory |

Icarus/Vivado simulation is optional for quick local inspection, but mandatory
for release validation and proof packaging.

## 1. Unit Tests

1. **Golden Model Comparison**: Use `golden_gkp_model.py` to generate expected outputs for a variety of inputs and compare them against the Verilog decoder via simulation.
2. **PRBS Trigger Test**: Simulate `prbs_gen` and confirm the trigger word appears at the correct sequence position.
3. **Soft Weighting Pipeline**: Verify that the pipelined `soft_weighting` produces the same result as a reference Python implementation and has consistent latency.
4. **Polynomial Evaluation**: Check that `poly_eval` correctly evaluates cubic polynomials across the full dynamic range.
5. **Safety Monitor**: Test that `safety_monitor` latches faults and clears correctly when `clear_faults` is asserted.

## 2. RTL Sanity

Run the provided `rtl_sanity_check.py` script to check for:

- Missing resets on sequential elements
- Undriven or multiply driven signals
- Implicit width mismatches

Use Verilator’s lint mode to catch synthesis problems early.

## 3. Simulation

1. **PRBS End‑to‑End**: Simulate the entire `waveform_control_4q_top` with PRBS enabled. Verify that the PRBS sequence flows through the decoders and packetizer without bit errors.
2. **Random Input Sweep**: Apply random ADC samples across the full range and compare the decoder output and syndrome bits with the Python model.
3. **Safety Fault Injection**: Force an over‑range condition on the ADC input and ensure `safety_kill` asserts and remains latched until cleared.
4. **Telemetry Counting**: Apply a known sequence of syndrome flips and verify that the `telemetry_flip_count` register reports the expected number of flips.

## 4. Hardware Bring‑Up

Follow the **Board Verification Checklist**. In particular:

1. **PRBS + ILA**: Confirm bit‑clean transmission and stable latency across power cycles.
2. **RF Loopback**: Verify analog path integrity and measure latency.
3. **Safety Kill Test**: Trigger the kill threshold and verify latched faults.
4. **Low‑Power Optics**: Measure shot noise and confirm LO phase sweep behavior.
5. **FSM Phases**: Step through the calibration FSM manually and ensure each stage functions as expected.

## 5. Documentation

Create a report that captures the validation results, including oscillogram screenshots, PRBS captures, and any anomalies. Use these results to refine the design and update the firmware and RTL where necessary.

## Health Monitor Validation

During simulation or hardware bring-up, verify:

1. `HEALTH_SAFETY_TRIPS` increments on the rising edge of a latched safety fault.
2. `HEALTH_AXIS_STALLS` increments only when `m_axis_tvalid=1` and `m_axis_tready=0`.
3. `HEALTH_DEC_VALID` increments while any decoder lane asserts valid output.
4. `HEALTH_TELEM_DONE` increments when a telemetry sample completes.
5. All health counters clear when the clear-faults/control clear is asserted.

## AXI-Lite Handshake Validation

For `axilite_regfile.v`, verify:

1. `AWREADY` and `WREADY` pulse only when both `AWVALID` and `WVALID` are asserted and the write channel is idle.
2. Register writes apply one clock after address/data capture.
3. `BVALID` pulses after the write is accepted.
4. `ARREADY` pulses only when `ARVALID` is asserted and the read channel is idle.
5. `RVALID` pulses with the expected register value one clock after address capture.
6. `CLEAR_FAULTS`, `TELEM_START`, and `TELEM_CLEAR` are one-cycle pulses.
7. Writable registers honor `WSTRB` byte enables.

## Golden-to-RTL Co-Simulation

Before Vivado implementation, run:

```bash
make cosim-vectors
python3 scripts/run_gkp_cosim.py
```

If `iverilog` is unavailable, import `sim/gkp_cosim_vectors.hex` into Vivado xsim and run `sim/tb_gkp_decoder_cosim.sv`.

Pass criteria:

1. Every generated vector reaches `valid_out`.
2. `adc_corr` matches the Python fixed-point expected result.
3. `syndrome` matches the Python expected syndrome.
4. No timeout occurs within `MAX_WAIT`.

## Full AXI4-Lite Wrapper Validation

Before using `axilite_regfile_full.v` on hardware, run protocol simulation:

1. AW before W.
2. W before AW.
3. AW and W in same cycle.
4. Read while write response is outstanding.
5. Backpressured `BREADY`.
6. Backpressured `RREADY`.
7. Unmapped address returns `SLVERR`.
8. Pulse registers assert for one cycle only.

## CDC Hardening v0.14 Validation

Use `waveform_brain_axi4lite_cdc_top` for any build where AXI-Lite and fabric
clocks are not the same.

Required checks:

1. Run implementation with `WB_TOP=waveform_brain_axi4lite_cdc_top`.
2. Run `source scripts/build_gate_cdc.tcl`.
3. Confirm `reports/cdc_critical_summary.json` passes.
4. Confirm `reports/cdc_cell_match_summary.md` reports non-zero matches for all centralized CDC wrapper patterns.
5. Fill out `docs/PHASE1_SIGNOFF_SHEET.md`.
6. Run `python3 scripts/package_cdc_signoff.py` after all reports exist.

Stop immediately if any direct AXI-register-to-fabric path appears outside
`waveform_brain_cdc_wrapper.v`.

## Pre-Board Gate v0.15 Validation

Before flashing hardware:

1. Run `make preboard-check`.
2. Run Vivado implementation using `scripts/waveform_brain_bitstream.tcl`.
3. Confirm the CDC gate passes.
4. Confirm `python3 scripts/implementation_gate.py` passes.
5. Run `make vivado-signoff-package`.
6. Fill out `docs/BOARD_READY_TEMPLATE.md`.
7. Fill out `docs/PHASE1_SIGNOFF_SHEET.md`.

Board testing is blocked if any required report is missing or any required gate fails.
