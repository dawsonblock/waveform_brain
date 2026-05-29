# AXI-Lite Control-Plane Hardening v0.11

The previous `axilite_regfile.v` was a simplified always-ready register file. It
worked as a scaffold, but it could create race-like behavior when the control
plane writes configuration while the fabric is active.

v0.11 replaces that model with a deterministic lightweight handshake design.

## What changed

- `AWREADY`, `WREADY`, and `ARREADY` are no longer constant-high combinational outputs.
- Write address/data are accepted only when both `AWVALID` and `WVALID` are high.
- Writes are applied one cycle after capture.
- `BVALID` is generated as an explicit response pulse.
- Reads capture `ARADDR` and return data one cycle later.
- `RVALID` is generated as an explicit response pulse.
- `CLEAR_FAULTS`, `TELEM_START`, and `TELEM_CLEAR` are pulse-style outputs instead of sticky register bits.
- `WSTRB` byte enables are honored for writable 32-bit registers.

## Important limitation

The scaffold interface still does not expose `BREADY`, `RREADY`, or 2-bit
`BRESP/RRESP`. A fully standards-complete AXI4-Lite slave should add those
signals or use the Xilinx AXI-Lite Slave IP template.

Within the existing project interface, this is a correctness and determinism
upgrade over the old always-ready combinational model.

## Firmware impact

Pulse registers now behave as write-only command strobes:

- write `1` to `CLEAR_FAULTS`
- write `1` to `TELEM_CTRL[0]` to start a telemetry sample
- write `1` to `TELEM_CTRL[1]` to clear telemetry totals

Reading these command locations returns `0`.

## Next gate

This still needs Vivado elaboration and simulation. The next control-plane
upgrade, if needed, is a standards-complete AXI4-Lite slave with:

- `BREADY`
- `RREADY`
- 2-bit `BRESP`
- 2-bit `RRESP`
- optional CDC synchronizers between AXI and fabric domains
