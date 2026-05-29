# Streaming Robustness and Calibration Observability v0.19

v0.19 focuses on preventing silent packet loss and making calibration output more auditable.

## Added RTL

- `rtl/axis_skid_buffer.v` (simulation-only; not instantiated in deployed hardware design)
- `rtl/axis_packet_fifo.v`

## Updated RTL

- `rtl/packer_axis.v`
- `rtl/waveform_control_4q_top.v`
- `rtl/waveform_brain_cdc_wrapper.v`
- `rtl/waveform_brain_axi4lite_cdc_top.v`
- `rtl/axilite_regfile_full.v`

## Streaming changes

`packer_axis.v` now emits packet format version `4'h2`.

Beat layout:

```text
Beat 0:
  [15:0]   data0
  [31:16]  data1
  [47:32]  data2
  [63:48]  data3

Beat 1:
  [63:48]  metadata
  [47:32]  reserved
  [31:0]   sequence counter
```

Metadata:

```text
meta[15:12] = 4'h2
meta[11:9]  = reserved
meta[8]     = fault_latched
meta[7:6]   = syndrome3
meta[5:4]   = syndrome2
meta[3:2]   = syndrome1
meta[1:0]   = syndrome0
```

## FIFO buffering

A synchronous AXI packet FIFO now sits after the packer:

```text
packer_axis -> axis_packet_fifo -> DMA/host stream
```

This absorbs short downstream stalls and exposes diagnostics.

`axis_packet_fifo.v` now drives `{m_axis_tlast, m_axis_tdata}` to zero when
empty while keeping `m_axis_tvalid=0`, which improves simulation/formal
readability without changing handshake semantics.

## New AXI-Lite readback registers

```text
0x5C WB_REG_AXIS_FIFO_LEVEL
0x60 WB_REG_AXIS_FIFO_OVERFLOW
0x64 WB_REG_AXIS_FIFO_STALLS
0x68 WB_REG_AXIS_FRAME_DROPS
0x6C WB_REG_AXIS_SEQUENCE
```

`WB_REG_AXIS_FRAME_DROPS` is the packer busy-valid-cycle counter: it increments
when a complete input frame is present while the two-beat packetizer is still
busy. It is a conservative pressure indicator, not an exact decoded-frame loss
counter under all traffic patterns.

## Host validation

Added:

- `userspace/validate_packet_capture.py`

It validates:

- two-beat packet alignment
- packet version
- sequence monotonicity
- syndrome range
- fault-packet count

## Formal/assertion support

Added:

- `formal/packer_axis_properties.sv`

The assertions check that `TVALID`, `TDATA`, and `TLAST` stay stable while stalled.

## Remaining limitation

The decoder path still does not have full upstream backpressure. The new packer counts frames that arrive while it is busy, and the FIFO absorbs downstream stalls, but a future fully lossless design should add a ready/valid contract at the decoder-wrapper boundary.
