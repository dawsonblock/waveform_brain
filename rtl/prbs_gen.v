// prbs_gen.v
// Generates a PRBS31 sequence with a specific trigger word for ILA capture.
// The PRBS outputs 31-bit data words along with a trigger flag when a
// predetermined pattern is present. This module is synchronous to the
// provided clock and resets with rst_n.

module prbs_gen (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       enable,
    output logic [30:0] prbs_out,
    output logic       trigger
);

    // 31‑bit PRBS register (x^31 + x^28 + 1)
    logic [30:0] prbs_reg;

    // Parameter for the trigger word pattern
    localparam logic [30:0] TRIGGER_WORD = 31'h2CCE551; // 0x2CCE5515 >> 1

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            prbs_reg <= 31'h7FFFFFFF;
        end else if (enable) begin
            // LFSR tap: x^31 + x^28 + 1
            logic feedback;
            feedback = prbs_reg[30] ^ prbs_reg[27];
            prbs_reg <= {prbs_reg[29:0], feedback};
        end
    end

    assign prbs_out = prbs_reg;
    assign trigger  = (prbs_reg == TRIGGER_WORD);

endmodule