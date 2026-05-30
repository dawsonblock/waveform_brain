`timescale 1ns/1ps

// gkp_decoder.v
//
// Pipelined soft-decision square-GKP-style decoder for one quadrature.
// v0.9 cleanup:
//   - Explicit stage boundaries for lattice snap, polynomial/weighting, and combine.
//   - Uses divider-free soft_weighting.v.
//   - Aligns position/syndrome with poly/weight latency.
//   - Adds a register before saturation to shorten the final timing path.


module gkp_decoder #(
    parameter int ADC_WIDTH   = 16,
    parameter int SCALE_WIDTH = 32
)(
    input  logic                         clk,
    input  logic                         rst_n,

    // Input sample from ADC
    input  logic signed [ADC_WIDTH-1:0]  adc_in,
    input  logic                         valid_in,

    // Lattice scaling parameters
    input  logic signed [SCALE_WIDTH-1:0] inv_delta_q, // reciprocal lattice scale, Q15.16
    input  logic signed [SCALE_WIDTH-1:0] delta_adc_q, // lattice spacing in ADC counts, Q15.16

    // Cubic polynomial coefficients, Q15.16
    input  logic signed [31:0]           coeffs [0:3],

    // Soft weighting parameter
    input  logic [15:0]                  alpha,

    // Outputs
    output logic                         valid_out,
    output logic signed [ADC_WIDTH-1:0]  adc_corr,
    output logic [1:0]                   syndrome
);

    localparam int FRAC_BITS = 16;
    localparam logic signed [31:0] ADC_MAX_32 = (32'sd1 <<< (ADC_WIDTH-1)) - 1;
    localparam logic signed [31:0] ADC_MIN_32 = -(32'sd1 <<< (ADC_WIDTH-1));

    function automatic logic signed [ADC_WIDTH-1:0] sat_adc(input logic signed [31:0] value);
        begin
            if (value > ADC_MAX_32) begin
                sat_adc = ADC_MAX_32[ADC_WIDTH-1:0];
            end else if (value < ADC_MIN_32) begin
                sat_adc = ADC_MIN_32[ADC_WIDTH-1:0];
            end else begin
                sat_adc = value[ADC_WIDTH-1:0];
            end
        end
    endfunction

    // ---------------------------------------------------------------------
    // Stage 1: multiply ADC sample by reciprocal lattice scale.
    // ---------------------------------------------------------------------
    logic signed [63:0]                  scaled_full_s1;
    logic signed [ADC_WIDTH-1:0]         adc_s1;
    logic                                valid_s1;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            scaled_full_s1 <= '0;
            adc_s1         <= '0;
            valid_s1       <= 1'b0;
        end else begin
            valid_s1       <= valid_in;
            adc_s1         <= adc_in;
            scaled_full_s1 <= adc_in * inv_delta_q;
        end
    end

    // ---------------------------------------------------------------------
    // Stage 2: round to nearest lattice index, compute position/remainder.
    // ---------------------------------------------------------------------
    logic signed [63:0]                  scaled_idx_full_comb;
    logic signed [15:0]                  lattice_idx_comb;
    logic signed [63:0]                  pos_full_comb;
    logic signed [31:0]                  pos_int_comb;
    logic signed [31:0]                  remainder_int_comb;
    logic signed [31:0]                  adc_s1_ext_comb;

    always_comb begin
        scaled_idx_full_comb = (scaled_full_s1 + 64'sd32768) >>> FRAC_BITS;

        if (scaled_idx_full_comb > 64'sd32767) begin
            lattice_idx_comb = 16'sh7FFF;
        end else if (scaled_idx_full_comb < -64'sd32768) begin
            lattice_idx_comb = -16'sh8000;
        end else begin
            lattice_idx_comb = scaled_idx_full_comb[15:0];
        end

        pos_full_comb   = $signed(lattice_idx_comb) * $signed(delta_adc_q);
        pos_int_comb    = pos_full_comb >>> FRAC_BITS;
        adc_s1_ext_comb = {{(32-ADC_WIDTH){adc_s1[ADC_WIDTH-1]}}, adc_s1};
        remainder_int_comb = adc_s1_ext_comb - pos_int_comb;
    end

    logic signed [ADC_WIDTH-1:0]         remainder_s2;
    logic signed [ADC_WIDTH-1:0]         pos_s2;
    logic [1:0]                          syndrome_s2;
    logic                                valid_s2;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            remainder_s2 <= '0;
            pos_s2       <= '0;
            syndrome_s2  <= 2'b0;
            valid_s2     <= 1'b0;
        end else begin
            valid_s2     <= valid_s1;
            pos_s2       <= sat_adc(pos_int_comb);
            remainder_s2 <= sat_adc(remainder_int_comb);
            syndrome_s2  <= lattice_idx_comb[1:0];
        end
    end

    // ---------------------------------------------------------------------
    // Stage 3/4/5: polynomial and soft weighting in parallel.
    // poly_eval latency       : 3 cycles from valid_s2
    // soft_weighting latency  : 3 cycles from valid_s2
    // ---------------------------------------------------------------------
    logic                                poly_valid;
    logic signed [31:0]                  poly_out;
    logic                                weight_valid;
    logic [15:0]                         weight_q8_8;

    poly_eval poly_eval_inst (
        .clk       (clk),
        .rst_n     (rst_n),
        .valid_in  (valid_s2),
        .x         ({{(32-ADC_WIDTH){remainder_s2[ADC_WIDTH-1]}}, remainder_s2}),
        .coeffs    (coeffs),
        .valid_out (poly_valid),
        .result    (poly_out)
    );

    soft_weighting #(
        .WIDTH(16),
        .OUT_FRAC(8),
        .RECIP_FRAC(24),
        .RECIP_WIDTH(25),
        .RECIP_FILE("reciprocal_lut_w16_q24w25.mem")
    ) soft_weighting_inst (
        .clk       (clk),
        .rst_n     (rst_n),
        .valid_in  (valid_s2),
        .alpha     (alpha),
        .r_in      (remainder_s2),
        .valid_out (weight_valid),
        .weight    (weight_q8_8)
    );

    // Align position and syndrome with poly/weight outputs.
    logic signed [ADC_WIDTH-1:0]         pos_d0, pos_d1, pos_d2;
    logic [1:0]                          syn_d0, syn_d1, syn_d2;
    logic                                meta_v0, meta_v1, meta_v2;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pos_d0  <= '0; pos_d1  <= '0; pos_d2  <= '0;
            syn_d0  <= 2'b0; syn_d1 <= 2'b0; syn_d2 <= 2'b0;
            meta_v0 <= 1'b0; meta_v1 <= 1'b0; meta_v2 <= 1'b0;
        end else begin
            pos_d0  <= pos_s2;
            pos_d1  <= pos_d0;
            pos_d2  <= pos_d1;

            syn_d0  <= syndrome_s2;
            syn_d1  <= syn_d0;
            syn_d2  <= syn_d1;

            meta_v0 <= valid_s2;
            meta_v1 <= meta_v0;
            meta_v2 <= meta_v1;
        end
    end

    // ---------------------------------------------------------------------
    // Stage 6: multiply polynomial correction by Q8.8 weight.
    // ---------------------------------------------------------------------
    logic signed [63:0]                  weighted_product_comb;
    logic signed [31:0]                  weighted_corr_s6;
    logic signed [ADC_WIDTH-1:0]         pos_s6;
    logic [1:0]                          syndrome_s6;
    logic                                valid_s6;

    always_comb begin
        weighted_product_comb = poly_out * $signed({1'b0, weight_q8_8});
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            weighted_corr_s6 <= '0;
            pos_s6           <= '0;
            syndrome_s6      <= 2'b0;
            valid_s6         <= 1'b0;
        end else begin
            valid_s6         <= poly_valid & weight_valid & meta_v2;
            weighted_corr_s6 <= weighted_product_comb >>> 8;
            pos_s6           <= pos_d2;
            syndrome_s6      <= syn_d2;
        end
    end

    // ---------------------------------------------------------------------
    // Stage 7: add position and correction.
    // ---------------------------------------------------------------------
    logic signed [31:0]                  sum_s7;
    logic [1:0]                          syndrome_s7;
    logic                                valid_s7;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sum_s7      <= '0;
            syndrome_s7 <= 2'b0;
            valid_s7    <= 1'b0;
        end else begin
            valid_s7    <= valid_s6;
            sum_s7      <= $signed(pos_s6) + weighted_corr_s6;
            syndrome_s7 <= syndrome_s6;
        end
    end

    // ---------------------------------------------------------------------
    // Stage 8: saturate and output.
    // ---------------------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            adc_corr  <= '0;
            syndrome  <= 2'b0;
            valid_out <= 1'b0;
        end else begin
            valid_out <= valid_s7;
            syndrome  <= syndrome_s7;

            if (sum_s7 > ADC_MAX_32) begin
                adc_corr <= ADC_MAX_32[ADC_WIDTH-1:0];
            end else if (sum_s7 < ADC_MIN_32) begin
                adc_corr <= ADC_MIN_32[ADC_WIDTH-1:0];
            end else begin
                adc_corr <= sum_s7[ADC_WIDTH-1:0];
            end
        end
    end

endmodule
