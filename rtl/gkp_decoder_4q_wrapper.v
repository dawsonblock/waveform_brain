// gkp_decoder_4q_wrapper.v
// Wrapper for four-parallel gkp_decoder instances. Each channel processes
// independent ADC inputs and produces corrected outputs. The parameters and
// coefficients are shared across channels.

module gkp_decoder_4q_wrapper #(
    parameter int ADC_WIDTH   = 16,
    parameter int SCALE_WIDTH = 32
)(
    input  logic                       clk,
    input  logic                       rst_n,
    input  logic [3:0]                 valid_in,
    input  logic signed [ADC_WIDTH-1:0] adc_in [0:3],
    input  logic signed [SCALE_WIDTH-1:0] inv_delta_q,
    input  logic signed [SCALE_WIDTH-1:0] delta_adc_q,
    input  logic signed [31:0]         coeffs [0:3],
    input  logic [15:0]               alpha,
    output logic [3:0]                 valid_out,
    output logic signed [ADC_WIDTH-1:0] adc_corr [0:3],
    // Syndrome bits for each decoder (two bits per channel)
    output logic [1:0]                 syndrome [0:3]
);

    genvar i;
    generate
        for (i = 0; i < 4; i++) begin : DEC
            gkp_decoder #(.ADC_WIDTH(ADC_WIDTH), .SCALE_WIDTH(SCALE_WIDTH)) dec_inst (
                .clk       (clk),
                .rst_n     (rst_n),
                .adc_in    (adc_in[i]),
                .valid_in  (valid_in[i]),
                .inv_delta_q(inv_delta_q),
                .delta_adc_q(delta_adc_q),
                .coeffs    (coeffs),
                .alpha     (alpha),
                .valid_out (valid_out[i]),
                .adc_corr  (adc_corr[i]),
                .syndrome  (syndrome[i])
            );
        end
    endgenerate

endmodule