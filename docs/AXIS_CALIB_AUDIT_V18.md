# AXI Packetizer, Calibration, and Arithmetic Audit Upgrade v0.18

v0.18 focuses on three remaining weak spots identified after the v0.17 flow hardening.

## 1. AXI4-Stream packetizer correction

`rtl/packer_axis.v` now holds `TVALID`, `TDATA`, and `TLAST` stable until
`TREADY` accepts each beat.

The previous behavior asserted `TVALID` only when `TREADY` was high. That is not
proper AXI4-Stream behavior and can hide stalls from downstream DMA/debug logic.

Current packet format:

- Beat 0: four corrected 16-bit words.
- Beat 1: metadata in bits `[63:48]`.

Metadata now includes a format version:

```text
meta[15:12] = 4'h1
meta[11:9]  = reserved
meta[8]     = fault_latched
meta[7:6]   = syndrome3
meta[5:4]   = syndrome2
meta[3:2]   = syndrome1
meta[1:0]   = syndrome0
```

Limitation: there is still no upstream ready signal. If the decoder produces
frames faster than the DMA accepts them, the integration should add a deeper FIFO
or backpressure-capable wrapper.

## 2. Calibration FSM improvement

`firmware/calibration_fsm.c` now includes:

- telemetry window start/wait helpers
- flip-delta measurement helper
- alpha grid-search tuning based on syndrome flip minimization
- settle delay after register writes

LO phase sweep and lattice scale sweep remain explicit board-specific hooks
because they require DAC/RFDC control not defined in the scaffold.

## 3. Register header repair

`firmware/registers.h` had health monitor definitions after the `#endif`.
v0.18 moves all register definitions inside the include guard and adds telemetry
bit definitions.

## 4. RTL arithmetic audit

Added:

- `scripts/audit_rtl_arithmetic.py`
- Makefile target: `make audit-arith`

The script fails if runtime division appears in synthesizable RTL. This protects
against accidentally reintroducing divider timing risks after the soft-weighting
refactor.

## Required next checks

```bash
make validate
make preboard-check
```

Vivado CDC/timing/DRC gates are still required before board testing.
