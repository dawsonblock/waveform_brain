# Waveform Brain v1.0 Board Verification Checklist

**Rule:** No optics until PRBS/ILA, RF loopback, safety kill, and temperature stability pass.

Icarus/Vivado simulation is optional for exploration only. Release validation
and board proof packaging require simulator evidence and Vivado report gates.

The board smoke scaffold is fail-closed by contract until real hardware
adapters are implemented. See `board_tests/adapter_contract.py` for
`ADAPTER_CONTRACT_VERSION` and standardized blocked `reason_code` values.
Any blocked board smoke output is evidence of missing adapter implementation,
not a passing hardware result.

This checklist outlines the steps required to verify the Waveform Brain v1.0 hardware before connecting any optical components. It mirrors the pocket version provided earlier.

## Phase 0 — Pre-power checks

- Confirm the fan is spinning and airflow around the heatsink is unobstructed.
- Open Vivado Hardware Manager → System Monitor.
- Record the ambient temperature.
- Do not connect optical components or enable the laser shutter.

## Phase 1 — Bitstream proof

- Run the bitstream build and collect timing, DRC, utilization, implementation, and bitstream logs.
- Check for unconstrained clocks and setup/hold slack.
- Check for critical warnings in clock, reset, CDC, RFDC, or AXI domains.
- Flash the ZCU208 and confirm the UART / MicroBlaze console responds.
- Confirm AXI-Lite register read/write works.
- Record idle die temperature.

Pass criteria: The bitstream loads cleanly, control registers function, and temperature is stable.

## Phase 2 — PRBS + ILA determinism

- Enable PRBS test mode (register `0x0C`).
- Arm the ILA on trigger word `0xACCE5515`.
- Capture raw path, decoder stages, packet output, and status flags.
- Compare the capture against the golden model using the Python tools.
- Record the measured latency.
- Perform a cold boot at least three times.
- Confirm the measured latency returns to the same expected cycle count across cold boots.
- Check for unexpected overflow or saturation flags.

Pass criteria: PRBS is bit-clean, the ILA trace matches the expected pipeline, and latency is stable across cold boots.

## Phase 3 — RF loopback

- Connect RF-DAC → attenuator → RF-ADC.
- Use safe signal levels.
- Run sine, ramp, and known-pattern tests.
- Verify ADC capture quality and DAC amplitude control.
- Verify there is no clipping.
- Measure ADC-to-DAC loop latency.
- Monitor the die temperature during sustained streaming.

Pass criteria: Loopback works cleanly, no clipping, latency is stable, and temperature is controlled.

## Phase 4 — Safety test

- Connect `safety_kill` to a dummy load or LED first.
- Confirm the default state is safe.
- Confirm FPGA reset or power loss results in a safe state.
- Trigger a threshold violation and confirm the kill signal asserts.
- Confirm the fault is latched/logged.
- Confirm a manual reset is required before re-enabling.

Pass criteria: Safety behavior is predictable and repeatable.

## Phase 5 — Low-power optical bring-up

- Connect the balanced homodyne output to RF-ADC.
- Connect RF-DAC to the EOM through safe attenuation/amplification.
- Start with low LO power.
- Measure the electronic noise floor and shot-noise reference.
- Check homodyne balance.
- Run a manual LO phase sweep and confirm phase-dependent variance.

Pass criteria: The optical signal is stable, shot noise is visible, LO phase changes variance, and no clipping occurs.

## Phase 6 — Progressive FSM

Enable the calibration FSM stages one at a time and verify each completes cleanly:

1. RFDC / capture-link alignment
2. Latency measurement
3. Raw stream
4. LO phase sweep
5. LO phase lock
6. GKP scale sweep
7. Alpha tuning
8. Normal stream mode

Pass criteria: Each stage completes without repeated faults, saturation events, stream overruns, or thermal rise.

## Temperature Logging Points

Record die temperature at these points:

- Before bitstream flash
- After bitstream load / idle
- During PRBS run
- After PRBS run
- After each cold boot
- During RF loopback (start and peak)
- During raw optical capture
- During FSM calibration
- During streaming mode

Conservative bench rules:

| Die Temperature | Status | Action |
| --- | --- | --- |
| < 70°C | Good | Continue |
| 70–80°C | Watch | Monitor closely |
| 80–85°C | Caution | Improve airflow |
| > 85°C | Pause | Stop and improve cooling |

These are bench guardrails, not official device limits.
