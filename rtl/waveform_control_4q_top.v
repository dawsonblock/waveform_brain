// waveform_control_4q_top.v
// Top level integration for the Waveform Brain v1.0 square GKP path. This
// module instantiates the PRBS generator, four GKP decoders, safety
// monitor, and packet packer. It routes configuration via the AXI‑Lite
// register file.

module waveform_control_4q_top #(
    parameter int ADC_WIDTH   = 16,
    parameter int SCALE_WIDTH = 32
)(
    input  logic                        clk,
    input  logic                        rst_n,
    // ADC inputs from RFSoC converters
    input  logic signed [ADC_WIDTH-1:0] adc_in [0:3],
    // AXI‑Lite control interface (abstracted)
    input  logic                        prbs_enable,
    input  logic signed [SCALE_WIDTH-1:0] inv_delta_q,
    input  logic signed [SCALE_WIDTH-1:0] delta_adc_q,
    input  logic signed [31:0]           coeffs [0:3],
    input  logic [15:0]                  alpha,
    input  logic [ADC_WIDTH-1:0]         kill_threshold,
    input  logic                        clear_faults,
    // Telemetry control signals from AXI‑Lite
    input  logic                        telem_start_sample,
    input  logic                        telem_clear_total,
    input  logic [31:0]                 telem_window_cycles,
    // AXIS interface
    output logic [63:0]                 m_axis_tdata,
    output logic                        m_axis_tvalid,
    input  logic                        m_axis_tready,
    output logic                        m_axis_tlast,
    // Status outputs
    output logic                        safety_kill,
    output logic [15:0]                 fault_flags,
    output logic [15:0]                 status_word,
    // Telemetry outputs
    output logic [31:0]                 telem_flips_delta,
    output logic [31:0]                 telem_total_flips,
    output logic                        telem_sample_active,
    output logic                        telem_sample_done,
    // Health monitor outputs
    output logic [31:0]                 health_status,
    output logic [31:0]                 health_safety_trip_count,
    output logic [31:0]                 health_axis_stall_count,
    output logic [31:0]                 health_decoder_valid_count,
    output logic [31:0]                 health_telem_done_count,

    // Streaming diagnostics
    output logic [4:0]                  axis_fifo_level,
    output logic [31:0]                 axis_fifo_overflow_count,
    output logic [31:0]                 axis_fifo_stall_count,
    output logic [31:0]                 axis_frame_drop_count,
    output logic [31:0]                 axis_sequence_count
);

    // Internal PRBS generator source.
    // The same PRBS sample is fanned out to all channels when enabled.
    logic [30:0] prbs_word;
    logic        prbs_trigger;

    prbs_gen prbs_inst (
        .clk    (clk),
        .rst_n  (rst_n),
        .enable (prbs_enable),
        .prbs_out(prbs_word),
        .trigger(prbs_trigger)
    );

    logic signed [ADC_WIDTH-1:0] prbs_sample;
    logic signed [ADC_WIDTH-1:0] effective_adc [0:3];

    assign prbs_sample = $signed(prbs_word[ADC_WIDTH-1:0]);

    generate
        for (genvar ch = 0; ch < 4; ch++) begin : g_effective_adc
            assign effective_adc[ch] = prbs_enable ? prbs_sample : adc_in[ch];
        end
    endgenerate

    // Four-channel safety monitoring with aggregate kill output.
    logic [3:0] safety_fault_latched_ch;
    logic [3:0] safety_kill_ch;
    logic       safety_fault_latched;

    generate
        for (genvar ch = 0; ch < 4; ch++) begin : g_safety
            safety_monitor #(.ADC_WIDTH(ADC_WIDTH)) safety_mon_inst (
                .clk          (clk),
                .rst_n        (rst_n),
                .adc_in       (effective_adc[ch]),
                .kill_threshold(kill_threshold),
                .clear_faults (clear_faults),
                .safety_kill  (safety_kill_ch[ch]),
                .fault_latched(safety_fault_latched_ch[ch])
            );
        end
    endgenerate

    assign safety_kill = |safety_kill_ch;
    assign safety_fault_latched = |safety_fault_latched_ch;
    assign fault_flags = {12'b0, safety_fault_latched_ch};

    // GKP decoder wrapper
    logic [3:0] dec_valid_in;
    logic [3:0] dec_valid_out;
    logic signed [ADC_WIDTH-1:0] dec_out [0:3];
    // Syndrome outputs from decoders
    logic [1:0] dec_syndrome [0:3];
    assign dec_valid_in = {4{!safety_kill}}; // disable decoding on kill

    gkp_decoder_4q_wrapper #(.ADC_WIDTH(ADC_WIDTH), .SCALE_WIDTH(SCALE_WIDTH)) dec_wrap (
        .clk       (clk),
        .rst_n     (rst_n),
        .valid_in  (dec_valid_in),
        .adc_in    (effective_adc),
        .inv_delta_q(inv_delta_q),
        .delta_adc_q(delta_adc_q),
        .coeffs    (coeffs),
        .alpha     (alpha),
        .valid_out (dec_valid_out),
        .adc_corr  (dec_out),
        .syndrome  (dec_syndrome)
    );

    // Packet packer + local AXI-Stream FIFO.
    //
    // The packer converts one 4-lane decoder output into a two-beat packet.
    // The FIFO absorbs short DMA/host stalls and exposes counters so packet
    // loss/backpressure is visible instead of silent.
    logic [63:0] packer_tdata;
    logic        packer_tvalid;
    logic        packer_tready;
    logic        packer_tlast;

    packer_axis #(.DATA_WIDTH(ADC_WIDTH)) packer_inst (
        .clk              (clk),
        .rst_n            (rst_n),
        .clear            (clear_faults),
        .valid_in         (dec_valid_out),
        .data_in          (dec_out),
        .syndrome         (dec_syndrome),
        .fault_latched    (safety_fault_latched),
        .m_axis_tdata     (packer_tdata),
        .m_axis_tvalid    (packer_tvalid),
        .m_axis_tready    (packer_tready),
        .m_axis_tlast     (packer_tlast),
        .sequence_counter (axis_sequence_count),
        .frame_drop_count (axis_frame_drop_count)
    );

    axis_packet_fifo #(
        .DATA_WIDTH (64),
        .DEPTH      (16)
    ) axis_fifo_inst (
        .clk            (clk),
        .rst_n          (rst_n),
        .clear          (clear_faults),
        .s_axis_tdata   (packer_tdata),
        .s_axis_tvalid  (packer_tvalid),
        .s_axis_tready  (packer_tready),
        .s_axis_tlast   (packer_tlast),
        .m_axis_tdata   (m_axis_tdata),
        .m_axis_tvalid  (m_axis_tvalid),
        .m_axis_tready  (m_axis_tready),
        .m_axis_tlast   (m_axis_tlast),
        .level          (axis_fifo_level),
        .overflow_count (axis_fifo_overflow_count),
        .stall_count    (axis_fifo_stall_count)
    );

    // Status word layout (16b): [15]=safety_kill, [14:11]=dec_valid_out,
    // [10:0]=reserved.
    assign status_word = {safety_kill, dec_valid_out, 11'h0};

    // Telemetry counter for syndrome flip rate (windowed measurement)
    telemetry_counter telemetry_inst (
        .clk          (clk),
        .rst_n        (rst_n),
        .valid_in     (dec_valid_out),
        .syndrome     (dec_syndrome),
        .start_sample (telem_start_sample),
        .clear_total  (telem_clear_total),
        .window_cycles(telem_window_cycles),
        .sample_active(telem_sample_active),
        .sample_done  (telem_sample_done),
        .flips_delta  (telem_flips_delta),
        .total_flips  (telem_total_flips)
    );

    // Health monitor: counts runtime events that should not just be cleared
    // and forgotten. These counters help identify recurring stalls, repeated
    // safety trips, and telemetry activity over time.
    health_monitor health_inst (
        .clk                         (clk),
        .rst_n                       (rst_n),
        .clear                       (clear_faults),
        .safety_fault_latched        (safety_fault_latched),
        .safety_kill                 (safety_kill),
        .axis_tvalid                 (m_axis_tvalid),
        .axis_tready                 (m_axis_tready),
        .decoder_valid               (dec_valid_out),
        .telemetry_sample_active     (telem_sample_active),
        .telemetry_sample_done       (telem_sample_done),
        .safety_trip_count           (health_safety_trip_count),
        .axis_stall_cycle_count      (health_axis_stall_count),
        .decoder_valid_cycle_count   (health_decoder_valid_count),
        .telemetry_window_done_count (health_telem_done_count),
        .health_status               (health_status)
    );

endmodule