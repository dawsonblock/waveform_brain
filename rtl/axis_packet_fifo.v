// axis_packet_fifo.v
//
// Small synchronous AXI4-Stream FIFO for packet buffering between packer_axis
// and DMA/host streaming logic.
//
// This is not a clock-crossing FIFO. It assumes one clock domain.

module axis_packet_fifo #(
    parameter int DATA_WIDTH = 64,
    parameter int DEPTH      = 16
)(
    input  logic                  clk,
    input  logic                  rst_n,
    input  logic                  clear,

    input  logic [DATA_WIDTH-1:0] s_axis_tdata,
    input  logic                  s_axis_tvalid,
    output logic                  s_axis_tready,
    input  logic                  s_axis_tlast,

    output logic [DATA_WIDTH-1:0] m_axis_tdata,
    output logic                  m_axis_tvalid,
    input  logic                  m_axis_tready,
    output logic                  m_axis_tlast,

    output logic [$clog2(DEPTH+1)-1:0] level,
    output logic [31:0]           overflow_count,
    output logic [31:0]           stall_count
);

    localparam int AW = (DEPTH <= 2) ? 1 : $clog2(DEPTH);

    logic [DATA_WIDTH:0] mem [0:DEPTH-1]; // {tlast, tdata}
    logic [AW-1:0] wr_ptr;
    logic [AW-1:0] rd_ptr;
    logic [$clog2(DEPTH+1)-1:0] count;

    wire full  = (count == DEPTH[$clog2(DEPTH+1)-1:0]);
    wire empty = (count == '0);

    wire push = s_axis_tvalid && s_axis_tready;
    wire pop  = m_axis_tvalid && m_axis_tready;

    assign s_axis_tready = !full;
    assign m_axis_tvalid = !empty;
    // Drive known values when empty for cleaner sim/formal behavior.
    assign {m_axis_tlast, m_axis_tdata} = empty ? '0 : mem[rd_ptr];
    assign level = count;

    function automatic [31:0] sat_inc(input [31:0] value);
        if (value == 32'hFFFF_FFFF) begin
            sat_inc = 32'hFFFF_FFFF;
        end else begin
            sat_inc = value + 32'd1;
        end
    endfunction

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr         <= '0;
            rd_ptr         <= '0;
            count          <= '0;
            overflow_count <= 32'd0;
            stall_count    <= 32'd0;
        end else begin
            if (clear) begin
                wr_ptr         <= '0;
                rd_ptr         <= '0;
                count          <= '0;
                overflow_count <= 32'd0;
                stall_count    <= 32'd0;
            end else begin
                if (s_axis_tvalid && !s_axis_tready) begin
                    overflow_count <= sat_inc(overflow_count);
                end

                if (m_axis_tvalid && !m_axis_tready) begin
                    stall_count <= sat_inc(stall_count);
                end

                if (push) begin
                    mem[wr_ptr] <= {s_axis_tlast, s_axis_tdata};
                    wr_ptr <= (wr_ptr == DEPTH-1) ? '0 : wr_ptr + 1'b1;
                end

                if (pop) begin
                    rd_ptr <= (rd_ptr == DEPTH-1) ? '0 : rd_ptr + 1'b1;
                end

                unique case ({push, pop})
                    2'b10: count <= count + 1'b1;
                    2'b01: count <= count - 1'b1;
                    default: count <= count;
                endcase
            end
        end
    end

endmodule
