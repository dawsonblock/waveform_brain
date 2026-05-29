# Health Monitor

The health monitor converts sticky or transient runtime events into saturating
counters. A sticky fault tells the system to stop; a counter tells the operator
whether the problem was isolated or recurring.

## RTL block

File:

`rtl/health_monitor.v`

Inputs:

- `safety_fault_latched`
- `safety_kill`
- `axis_tvalid`
- `axis_tready`
- `decoder_valid`
- `telemetry_sample_active`
- `telemetry_sample_done`

Counters:

- `safety_trip_count`
- `axis_stall_cycle_count`
- `decoder_valid_cycle_count`
- `telemetry_window_done_count`

## Register map

| Address | Register | Meaning |
|---:|---|---|
| `0x48` | `HEALTH_STATUS` | Compact status bitfield |
| `0x4C` | `HEALTH_SAFETY_TRIPS` | Count of safety trip events |
| `0x50` | `HEALTH_AXIS_STALLS` | Count of AXI-Stream stall cycles |
| `0x54` | `HEALTH_DEC_VALID` | Count of decoder-valid cycles |
| `0x58` | `HEALTH_TELEM_DONE` | Count of completed telemetry windows |

## Status bits

| Bit | Name |
|---:|---|
| 0 | safety fault latched |
| 1 | safety kill asserted |
| 2 | AXI backpressure active now |
| 3 | any decoder lane valid now |
| 4 | telemetry sample active |
| 5 | telemetry sample done pulse |

## Why this matters

Do not just clear a sticky fault and continue. First read the counters. One
isolated event may be a transient. Repeated events indicate a throughput,
clocking, DMA, safety threshold, or calibration problem.

## Bring-up gate

During PRBS/ILA and RF loopback:

- `HEALTH_SAFETY_TRIPS` should remain zero.
- `HEALTH_AXIS_STALLS` should remain zero unless the downstream DMA intentionally applies backpressure.
- `HEALTH_DEC_VALID` should increase while the decoder is running.
- `HEALTH_TELEM_DONE` should increase only when telemetry windows complete.

If a counter grows unexpectedly, pause hardware progression and debug before
connecting optics.
