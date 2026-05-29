# GKP Golden-to-RTL Co-Simulation Harness v0.12

This package now includes a bit-for-bit harness for comparing the Python fixed-point model against `gkp_decoder.v`.

## Added files

- `scripts/generate_gkp_cosim_vectors.py`
- `scripts/run_gkp_cosim.py`
- `sim/tb_gkp_decoder_cosim.sv`

## Flow

Generate vectors:

```bash
python3 scripts/generate_gkp_cosim_vectors.py --count 64
```

Run Icarus Verilog co-sim:

```bash
python3 scripts/run_gkp_cosim.py
```

The runner requires `iverilog` and `vvp`. If those tools are not installed,
use the same vector file with Vivado xsim.

Icarus/Vivado simulation is optional for quick local exploration, but mandatory
for release validation and proof packaging.

## What is checked

For each vector, the testbench drives:

- `adc_in`
- `inv_delta_q`
- `delta_adc_q`
- `coeffs[0:3]`
- `alpha`

It waits for `valid_out`, then compares:

- `adc_corr`
- `syndrome`

against the expected Python fixed-point result.

## Important correction

v0.12 also fixes `poly_eval.v` so `x` is delayed through the Horner pipeline. Without that, streaming samples can be evaluated with mismatched pipeline operands.

## Status

This is a simulation harness, not hardware proof. Passing co-sim is the gate before Vivado implementation and PRBS/ILA board testing.
