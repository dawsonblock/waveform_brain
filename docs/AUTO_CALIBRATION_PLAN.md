# Auto‑Calibration Plan (v0.3)

This document outlines the design philosophy and proposed control flow for the Waveform Brain auto‑calibration system.  The goal is to tune the GKP decoder parameters without manual intervention by using measured telemetry as an objective function.

## Telemetry Overview

The hardware exposes a windowed syndrome flip counter via the AXI‑Lite register map.  To trigger a measurement, software writes a *start* pulse to `TELEM_CTRL[0]` and specifies the length of the measurement window (in clock cycles) in `TELEM_WINDOW`.  The hardware returns:

* `TELEM_FLIPS_DELTA` – the number of syndrome flips detected during the last completed window.
* `TELEM_TOTAL_FLIPS` – a running total of all flips since the last clear.
* `TELEM_STATUS[0]` – high while a window is active.
* `TELEM_STATUS[1]` – pulses high for one cycle at the end of the window.

The auto‑calibration logic measures **flip rate** by dividing `flips_delta` by `window_cycles`.  Lower flip rates correspond to more reliable decoding.

## Calibration Phases

1. **Digital sanity check**
   * Enable PRBS and verify deterministic latency and bit‑perfect data using the board verification checklist.
2. **Cold calibration**
   * With PRBS disabled but no optical input, measure and null ADC/DAC offsets.
3. **LO phase lock**
   * Sweep the LO phase (via DAC or external controller) and use the flip rate to identify the phase giving minimum syndrome flips.  A grid search on phase, followed by local refinement, is preferred over gradient descent because the objective can be noisy or non‑convex.
4. **Lattice scaling**
   * Sweep `DELTA_ADC_Q` and use the flip rate to select the scale that minimises syndrome flips.  Again, perform a coarse grid search followed by local refinement.
5. **Alpha tuning**
   * Sweep the soft‑weight parameter `ALPHA`.  Use flip rate as the objective.  Start with a wide range, then refine around the minimum.
6. **Normal operation**
   * After tuning, clear the telemetry total counter and begin streaming.  Periodically measure flip rate to detect drift.  If the rate increases beyond a threshold, repeat the tuning phases.

## Software Helper Functions

The firmware (or host software) should implement small helper routines:

```c
// Start a telemetry measurement and return the delta and status when done
static void start_telemetry_sample(uint32_t window_cycles) {
    wb_write(WB_REG_TELEM_WINDOW, window_cycles);
    // Pulse start bit
    wb_write(WB_REG_TELEM_CTRL, 0x1);
    wb_write(WB_REG_TELEM_CTRL, 0x0);
    // Poll until TELEM_STATUS[1] (sample_done) is set
    while ((wb_read(WB_REG_TELEM_STATUS) & 0x2) == 0) { /* spin */ }
}

static uint32_t read_flip_delta(void) {
    return wb_read(WB_REG_TELEM_FLIPS_DELTA);
}

static uint32_t compute_flip_rate_ppm(uint32_t flips, uint32_t cycles) {
    // parts per million of flips per cycle
    return (flips * 1000000u) / cycles;
}
```

Higher‑level sweep routines can then call these helpers to evaluate the flip rate at different parameter values.

## Notes

* **Sample window length:** A measurement window must be long enough to average out random fluctuations but short enough to allow responsive tuning.  Start with 1e6 cycles and adjust based on empirical variance.
* **Saturation handling:** Always check `FAULT_FLAGS` before initiating a measurement.  Abort calibration if the safety monitor trips or the decoder saturates.
* **Backpressure:** The telemetry system runs independently of the AXI‑Stream data path.  Ensure that DMA and streaming buffers are not overrun during calibration by either disabling streaming or providing sufficient FIFO depth.
