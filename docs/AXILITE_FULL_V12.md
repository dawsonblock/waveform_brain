# Full AXI4-Lite Wrapper v0.12

This package now includes an optional standards-oriented AXI4-Lite control-plane path.

## Added RTL

- `rtl/axilite_regfile_full.v`
- `rtl/waveform_brain_axi4lite_full_top.v`

## Why it exists

The earlier `axilite_regfile.v` is a lightweight scaffold interface. v0.11 improved its handshake behavior, but it still does not expose `BREADY`, `RREADY`, or 2-bit response signals.

`axilite_regfile_full.v` adds:

- independent AW and W channel capture
- `BREADY`
- `RREADY`
- 2-bit `BRESP`
- 2-bit `RRESP`
- explicit `SLVERR` response on unmapped addresses
- byte-write handling through `WSTRB`
- pulse-style command outputs for clear and telemetry control

## Integration note

`waveform_brain_axi4lite_full_top.v` assumes the AXI-Lite clock and fabric clock are the same. If they differ, insert explicit CDC wrappers between the register file and the fabric core.

This is not hardware-proven. Run Vivado elaboration and protocol simulation before board use.
