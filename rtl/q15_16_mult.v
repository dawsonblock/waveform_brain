// q15_16_mult.v
// This module performs a fixed-point multiplication on two Q15.16 numbers.
// It produces a 32-bit result with saturation and optional rounding. The
// multiplier uses a 64-bit accumulator to avoid overflow. This version
// remains unchanged from the previous scaffold.

module q15_16_mult (
    input  logic         clk,
    input  logic         rst_n,
    input  logic         valid_in,
    input  logic signed [31:0]  a,
    input  logic signed [31:0]  b,
    output logic         valid_out,
    output logic signed [31:0]  result,
    output logic         overflow
);

    // Internal pipeline register holding the sampled product for this cycle.
    logic signed [63:0] mult_full_reg;
    logic valid_reg;

    logic signed [63:0] mult_full_next;
    logic signed [63:0] rounded_full;
    logic overflow_comb;

    assign mult_full_next = a * b;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mult_full_reg <= '0;
            valid_reg    <= 1'b0;
        end else begin
            valid_reg    <= valid_in;
            // Sample product so valid/result/overflow remain cycle-aligned.
            mult_full_reg <= mult_full_next;
        end
    end

    // Truncate to Q15.16 result with rounding by adding half LSB.
    logic signed [31:0] rounded;
    always_comb begin
        // Add 2^15 before extracting [47:16].
        rounded_full = mult_full_reg + 64'sh0000_0000_0000_8000;
        rounded      = rounded_full[47:16];
    end

    // Overflow if discarded upper bits are not sign extension of result.
    assign overflow_comb = (rounded_full[63:48] != {16{rounded_full[47]}});

    assign valid_out = valid_reg;
    assign result    = rounded;
    assign overflow  = overflow_comb;

endmodule