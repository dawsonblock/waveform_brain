// axis_skid_buffer.v
//
// One-deep AXI4-Stream skid buffer.
// Holds payload stable during downstream stalls and preserves AXIS handshake.

module axis_skid_buffer #(
    parameter int DATA_WIDTH = 64
)(
    input  logic                  clk,
    input  logic                  rst_n,

    input  logic [DATA_WIDTH-1:0] s_axis_tdata,
    input  logic                  s_axis_tvalid,
    output logic                  s_axis_tready,
    input  logic                  s_axis_tlast,

    output logic [DATA_WIDTH-1:0] m_axis_tdata,
    output logic                  m_axis_tvalid,
    input  logic                  m_axis_tready,
    output logic                  m_axis_tlast
);

    logic [DATA_WIDTH-1:0] data_q;
    logic                  last_q;
    logic                  full_q;

    assign s_axis_tready = !full_q || (m_axis_tready && m_axis_tvalid);
    assign m_axis_tvalid = full_q;
    assign m_axis_tdata  = data_q;
    assign m_axis_tlast  = last_q;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            full_q <= 1'b0;
            data_q <= '0;
            last_q <= 1'b0;
        end else begin
            if (s_axis_tready && s_axis_tvalid) begin
                data_q <= s_axis_tdata;
                last_q <= s_axis_tlast;
                full_q <= 1'b1;
            end else if (m_axis_tready && m_axis_tvalid) begin
                full_q <= 1'b0;
            end
        end
    end

endmodule
