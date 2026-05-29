// soft_weighting.v
//
// Divider-free pipelined soft weighting.
//
// Computes approximately:
//     weight = alpha / (alpha + abs(r))
//
// Output format:
//     weight is Q8.8 by default.
//
// v0.10 hardening:
//   - No runtime "/" operator in the datapath.
//   - Reciprocal is read from a precomputed ROM initialized by a .mem file.
//   - Reciprocal width is RECIP_FRAC+1 so denom=1 can represent exactly 2^RECIP_FRAC.
//   - The datapath is fixed-latency: denom -> ROM lookup -> DSP multiply -> Q8.8 output.

module soft_weighting #(
    parameter int WIDTH        = 16,
    parameter int OUT_FRAC     = 8,
    parameter int RECIP_FRAC   = 24,
    parameter int RECIP_WIDTH  = RECIP_FRAC + 1,
    parameter string RECIP_FILE = "reciprocal_lut_w16_q24w25.mem"
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    valid_in,
    input  logic [WIDTH-1:0]        alpha,
    input  logic signed [WIDTH-1:0] r_in,
    output logic                    valid_out,
    output logic [WIDTH-1:0]        weight
);

    localparam int DENOM_WIDTH = WIDTH + 1;
    localparam int LUT_DEPTH   = (1 << DENOM_WIDTH);
    localparam int PROD_WIDTH  = WIDTH + RECIP_WIDTH;

    // Force block ROM inference where possible. Vivado may still choose
    // distributed memory depending on settings/device, but this attribute
    // documents the intended implementation.
    (* rom_style = "block" *) logic [RECIP_WIDTH-1:0] reciprocal_rom [0:LUT_DEPTH-1];

    initial begin
        $readmemh(RECIP_FILE, reciprocal_rom);
    end

    // Stage 1: absolute value and denominator.
    logic [WIDTH:0]          abs_r_s1;
    logic [DENOM_WIDTH-1:0]  denom_s1;
    logic [WIDTH-1:0]        alpha_s1;
    logic                    valid_s1;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            abs_r_s1 <= '0;
            denom_s1 <= '0;
            alpha_s1 <= '0;
            valid_s1 <= 1'b0;
        end else begin
            valid_s1 <= valid_in;
            alpha_s1 <= alpha;

            if (r_in[WIDTH-1]) begin
                // Cast to WIDTH+1 so -32768 becomes +32768 cleanly.
                abs_r_s1 <= {1'b0, (~r_in + 1'b1)};
                denom_s1 <= {1'b0, alpha} + {1'b0, (~r_in + 1'b1)};
            end else begin
                abs_r_s1 <= {1'b0, r_in};
                denom_s1 <= {1'b0, alpha} + {1'b0, r_in};
            end
        end
    end

    // Stage 2: reciprocal ROM lookup.
    logic [RECIP_WIDTH-1:0]  recip_s2;
    logic [WIDTH-1:0]        alpha_s2;
    logic                    valid_s2;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            recip_s2 <= '0;
            alpha_s2 <= '0;
            valid_s2 <= 1'b0;
        end else begin
            valid_s2 <= valid_s1;
            alpha_s2 <= alpha_s1;
            recip_s2 <= reciprocal_rom[denom_s1];
        end
    end

    // Stage 3: reciprocal multiply and output scaling.
    logic [PROD_WIDTH-1:0] product_comb;
    logic [PROD_WIDTH-1:0] product_rounded;
    logic [WIDTH-1:0]     weight_comb;
    logic                 valid_s3;

    always_comb begin
        product_comb = alpha_s2 * recip_s2;

        if (RECIP_FRAC > OUT_FRAC) begin
            product_rounded = product_comb + ({{(PROD_WIDTH-(RECIP_FRAC-OUT_FRAC)){1'b0}}, 1'b1} << (RECIP_FRAC - OUT_FRAC - 1));
            weight_comb = product_rounded >> (RECIP_FRAC - OUT_FRAC);
        end else begin
            weight_comb = product_comb << (OUT_FRAC - RECIP_FRAC);
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_s3 <= 1'b0;
            weight   <= '0;
        end else begin
            valid_s3 <= valid_s2;
            if (alpha_s2 == '0) begin
                weight <= '0;
            end else begin
                weight <= weight_comb;
            end
        end
    end

    assign valid_out = valid_s3;

endmodule
