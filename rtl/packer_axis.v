// packer_axis.v
//
// AXI4-Stream compliant two-beat packet packer for Waveform Brain.
//
// v0.19 packet format:
//
//   Beat 0: four corrected data words:
//     [15:0]   data0
//     [31:16]  data1
//     [47:32]  data2
//     [63:48]  data3
//
//   Beat 1:
//     [63:48] metadata
//     [47:32] reserved
//     [31:0]  sequence counter
//
// Metadata:
//     meta[15:12] packet format version = 4'h2 (legacy v1 used 4'h1)
//     meta[11:9]  reserved
//     meta[8]     fault_latched
//     meta[7:6]   syndrome3
//     meta[5:4]   syndrome2
//     meta[3:2]   syndrome1
//     meta[1:0]   syndrome0
//
// The module holds TVALID, TDATA, and TLAST stable until accepted.
// If a new frame arrives while the two-beat packeter is busy, it is counted in
// frame_drop_count. This is a visibility feature, not a substitute for upstream
// backpressure.


module packer_axis #(
module packer_axis #(
    parameter int DATA_WIDTH = 16
)(
    input  logic                     clk,
    input  logic                     rst_n,
    input  logic                     clear,
    input  logic [3:0]               valid_in,
    input  logic signed [DATA_WIDTH-1:0] data_in [0:3],
    input  logic [1:0]               syndrome [0:3],
    input  logic                     fault_latched,

    output logic [63:0]              m_axis_tdata,
    output logic                     m_axis_tvalid,
    input  logic                     m_axis_tready,
    output logic                     m_axis_tlast,

    output logic [31:0]              sequence_counter,
    output logic [31:0]              frame_drop_count
);

    typedef enum logic [1:0] {
        ST_IDLE  = 2'b00,
        ST_BEAT0 = 2'b01,
        ST_BEAT1 = 2'b10
    } state_t;

    state_t state;

    logic [15:0] meta_reg;
    logic [31:0] packet_seq_reg;

    function automatic [63:0] pack_data(
        input logic signed [DATA_WIDTH-1:0] d0,
        input logic signed [DATA_WIDTH-1:0] d1,
        input logic signed [DATA_WIDTH-1:0] d2,
        input logic signed [DATA_WIDTH-1:0] d3
    );
        pack_data = {d3[15:0], d2[15:0], d1[15:0], d0[15:0]};
    endfunction

    function automatic [15:0] pack_meta(
        input logic fault,
        input logic [1:0] s0,
        input logic [1:0] s1,
        input logic [1:0] s2,
        input logic [1:0] s3
    );
        pack_meta = {4'h2, 3'b000, fault, s3, s2, s1, s0};
    endfunction

    function automatic [31:0] sat_inc(input [31:0] value);
        if (value == 32'hFFFF_FFFF) begin
            sat_inc = 32'hFFFF_FFFF;
        end else begin
            sat_inc = value + 32'd1;
        end
    endfunction

    wire frame_in_valid = &valid_in;
    wire beat_accepted  = m_axis_tvalid && m_axis_tready;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state            <= ST_IDLE;
            m_axis_tdata     <= 64'd0;
            m_axis_tvalid    <= 1'b0;
            m_axis_tlast     <= 1'b0;
            meta_reg         <= 16'd0;
            packet_seq_reg   <= 32'd0;
            sequence_counter <= 32'd0;
            frame_drop_count <= 32'd0;
        end else begin
            if (clear) begin
                state            <= ST_IDLE;
                m_axis_tdata     <= 64'd0;
                m_axis_tvalid    <= 1'b0;
                m_axis_tlast     <= 1'b0;
                meta_reg         <= 16'd0;
                packet_seq_reg   <= 32'd0;
                sequence_counter <= 32'd0;
                frame_drop_count <= 32'd0;
            end else begin
                case (state)
                    ST_IDLE: begin
                        m_axis_tvalid <= 1'b0;
                        m_axis_tlast  <= 1'b0;

                        if (frame_in_valid) begin
                            packet_seq_reg   <= sequence_counter;
                            meta_reg         <= pack_meta(fault_latched, syndrome[0], syndrome[1], syndrome[2], syndrome[3]);
                            m_axis_tdata     <= pack_data(data_in[0], data_in[1], data_in[2], data_in[3]);
                            m_axis_tvalid    <= 1'b1;
                            m_axis_tlast     <= 1'b0;
                            sequence_counter <= sat_inc(sequence_counter);
                            state            <= ST_BEAT0;
                        end
                    end

                    ST_BEAT0: begin
                        // Hold beat 0 stable until accepted.
                        m_axis_tvalid <= 1'b1;
                        m_axis_tlast  <= 1'b0;

                        if (frame_in_valid) begin
                            frame_drop_count <= sat_inc(frame_drop_count);
                        end

                        if (beat_accepted) begin
                            m_axis_tdata <= {meta_reg, 16'd0, packet_seq_reg};
                            m_axis_tlast <= 1'b1;
                            state        <= ST_BEAT1;
                        end
                    end

                    ST_BEAT1: begin
                        // Hold beat 1 stable until accepted.
                        m_axis_tvalid <= 1'b1;
                        m_axis_tlast  <= 1'b1;

                        if (frame_in_valid) begin
                            frame_drop_count <= sat_inc(frame_drop_count);
                        end

                        if (beat_accepted) begin
                            m_axis_tvalid <= 1'b0;
                            m_axis_tlast  <= 1'b0;
                            state         <= ST_IDLE;
                        end
                    end

                    default: begin
                        state         <= ST_IDLE;
                        m_axis_tvalid <= 1'b0;
                        m_axis_tlast  <= 1'b0;
                    end
                endcase
            end
        end
    end

endmodule
