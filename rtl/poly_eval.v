// poly_eval.v
//
// Pipelined cubic polynomial evaluator using Horner's method.
// Coefficients are Q15.16 fixed-point. Input x is Q15.16.
// Result is Q15.16.
//
// v0.12 correction:
//   - Multiplier results are computed combinationally before the register.
//   - x is delayed through the pipeline so every Horner stage uses the same
//     sample, not the next streaming input.

module poly_eval #(
    parameter int COEFF_COUNT = 4
)(
    input  logic                     clk,
    input  logic                     rst_n,
    input  logic                     valid_in,
    input  logic signed [31:0]       x,
    input  logic signed [31:0]       coeffs [0:COEFF_COUNT-1],
    output logic                     valid_out,
    output logic signed [31:0]       result
);

    // Stage 1: coeff[3] * x + coeff[2]
    logic signed [63:0] stage1_mult_comb;
    logic signed [31:0] stage1_res;
    logic signed [31:0] x_s1;
    logic               stage1_valid;

    always_comb begin
        stage1_mult_comb = coeffs[3] * x;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage1_res   <= '0;
            x_s1         <= '0;
            stage1_valid <= 1'b0;
        end else begin
            stage1_valid <= valid_in;
            x_s1         <= x;
            stage1_res   <= ((stage1_mult_comb + 64'sh0000_0000_0000_8000) >>> 16) + coeffs[2];
        end
    end

    // Stage 2: stage1 * x + coeff[1]
    logic signed [63:0] stage2_mult_comb;
    logic signed [31:0] stage2_res;
    logic signed [31:0] x_s2;
    logic               stage2_valid;

    always_comb begin
        stage2_mult_comb = stage1_res * x_s1;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage2_res   <= '0;
            x_s2         <= '0;
            stage2_valid <= 1'b0;
        end else begin
            stage2_valid <= stage1_valid;
            x_s2         <= x_s1;
            stage2_res   <= ((stage2_mult_comb + 64'sh0000_0000_0000_8000) >>> 16) + coeffs[1];
        end
    end

    // Stage 3: stage2 * x + coeff[0]
    logic signed [63:0] stage3_mult_comb;
    logic signed [31:0] stage3_res;
    logic               stage3_valid;

    always_comb begin
        stage3_mult_comb = stage2_res * x_s2;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage3_res   <= '0;
            stage3_valid <= 1'b0;
        end else begin
            stage3_valid <= stage2_valid;
            stage3_res   <= ((stage3_mult_comb + 64'sh0000_0000_0000_8000) >>> 16) + coeffs[0];
        end
    end

    assign valid_out = stage3_valid;
    assign result    = stage3_res;

endmodule
