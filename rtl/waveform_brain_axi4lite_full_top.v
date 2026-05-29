// waveform_brain_axi4lite_full_top.v
//
// Optional integration wrapper that connects axilite_regfile_full.v to
// waveform_control_4q_top.v. This is intended for Vivado/IP integration when a
// fuller AXI4-Lite slave interface is required.
//
// This wrapper assumes the AXI-Lite clock and fabric clock are the same.
// If they differ, add explicit CDC wrappers between the register file and
// waveform_control_4q_top.

module waveform_brain_axi4lite_full_top #(
    parameter int ADC_WIDTH   = 16,
    parameter int SCALE_WIDTH = 32
)(
    input  logic                         s_axi_aclk,
    input  logic                         s_axi_aresetn,

    // ADC inputs
    input  logic signed [ADC_WIDTH-1:0]  adc_in [0:3],

    // AXI4-Lite slave
    input  logic [7:0]                   s_axi_awaddr,
    input  logic                         s_axi_awvalid,
    output logic                         s_axi_awready,
    input  logic [31:0]                  s_axi_wdata,
    input  logic [3:0]                   s_axi_wstrb,
    input  logic                         s_axi_wvalid,
    output logic                         s_axi_wready,
    output logic [1:0]                   s_axi_bresp,
    output logic                         s_axi_bvalid,
    input  logic                         s_axi_bready,
    input  logic [7:0]                   s_axi_araddr,
    input  logic                         s_axi_arvalid,
    output logic                         s_axi_arready,
    output logic [31:0]                  s_axi_rdata,
    output logic [1:0]                   s_axi_rresp,
    output logic                         s_axi_rvalid,
    input  logic                         s_axi_rready,

    // AXI-Stream output
    output logic [63:0]                  m_axis_tdata,
    output logic                         m_axis_tvalid,
    input  logic                         m_axis_tready,
    output logic                         m_axis_tlast,

    // External status
    output logic                         safety_kill
);

    logic prbs_enable;
    logic signed [SCALE_WIDTH-1:0] inv_delta_q;
    logic signed [SCALE_WIDTH-1:0] delta_adc_q;
    logic signed [31:0] coeffs [0:3];
    logic [15:0] alpha;
    logic [ADC_WIDTH-1:0] kill_threshold;
    logic clear_faults;

    logic [15:0] fault_flags;
    logic [15:0] status_word;

    logic [31:0] telem_flips_delta;
    logic [31:0] telem_total_flips;
    logic        telem_sample_active;
    logic        telem_sample_done;
    logic        telem_start_sample;
    logic        telem_clear_total;
    logic [31:0] telem_window_cycles;

    logic [31:0] health_status;
    logic [31:0] health_safety_trip_count;
    logic [31:0] health_axis_stall_count;
    logic [31:0] health_decoder_valid_count;
    logic [31:0] health_telem_done_count;

    localparam logic [31:0] BUILD_ID = 32'h5742_5631; // "WBV1"

    axilite_regfile_full u_regs (
        .s_axi_aclk                    (s_axi_aclk),
        .s_axi_aresetn                 (s_axi_aresetn),

        .s_axi_awaddr                  (s_axi_awaddr),
        .s_axi_awvalid                 (s_axi_awvalid),
        .s_axi_awready                 (s_axi_awready),
        .s_axi_wdata                   (s_axi_wdata),
        .s_axi_wstrb                   (s_axi_wstrb),
        .s_axi_wvalid                  (s_axi_wvalid),
        .s_axi_wready                  (s_axi_wready),
        .s_axi_bresp                   (s_axi_bresp),
        .s_axi_bvalid                  (s_axi_bvalid),
        .s_axi_bready                  (s_axi_bready),
        .s_axi_araddr                  (s_axi_araddr),
        .s_axi_arvalid                 (s_axi_arvalid),
        .s_axi_arready                 (s_axi_arready),
        .s_axi_rdata                   (s_axi_rdata),
        .s_axi_rresp                   (s_axi_rresp),
        .s_axi_rvalid                  (s_axi_rvalid),
        .s_axi_rready                  (s_axi_rready),

        .prbs_enable                   (prbs_enable),
        .inv_delta_q                   (inv_delta_q),
        .delta_adc_q                   (delta_adc_q),
        .coeffs                        (coeffs),
        .alpha                         (alpha),
        .kill_threshold                (kill_threshold),
        .clear_faults                  (clear_faults),

        .status_word_in                (status_word),
        .fault_flags_in                (fault_flags),
        .build_id                      (BUILD_ID),

        .telemetry_flips_delta_in      (telem_flips_delta),
        .telemetry_total_flips_in      (telem_total_flips),
        .telemetry_sample_active_in    (telem_sample_active),
        .telemetry_sample_done_in      (telem_sample_done),

        .health_status_in              (health_status),
        .health_safety_trip_count_in   (health_safety_trip_count),
        .health_axis_stall_count_in    (health_axis_stall_count),
        .health_decoder_valid_count_in (health_decoder_valid_count),
        .health_telem_done_count_in    (health_telem_done_count),

        .telem_start_sample            (telem_start_sample),
        .telem_clear_total             (telem_clear_total),
        .telem_window_cycles           (telem_window_cycles)
    );

    waveform_control_4q_top #(
        .ADC_WIDTH   (ADC_WIDTH),
        .SCALE_WIDTH (SCALE_WIDTH)
    ) u_core (
        .clk                        (s_axi_aclk),
        .rst_n                      (s_axi_aresetn),
        .adc_in                     (adc_in),

        .prbs_enable                (prbs_enable),
        .inv_delta_q                (inv_delta_q),
        .delta_adc_q                (delta_adc_q),
        .coeffs                     (coeffs),
        .alpha                      (alpha),
        .kill_threshold             (kill_threshold),
        .clear_faults               (clear_faults),

        .telem_start_sample         (telem_start_sample),
        .telem_clear_total          (telem_clear_total),
        .telem_window_cycles        (telem_window_cycles),

        .m_axis_tdata               (m_axis_tdata),
        .m_axis_tvalid              (m_axis_tvalid),
        .m_axis_tready              (m_axis_tready),
        .m_axis_tlast               (m_axis_tlast),

        .safety_kill                (safety_kill),
        .fault_flags                (fault_flags),
        .status_word                (status_word),

        .telem_flips_delta          (telem_flips_delta),
        .telem_total_flips          (telem_total_flips),
        .telem_sample_active        (telem_sample_active),
        .telem_sample_done          (telem_sample_done),

        .health_status              (health_status),
        .health_safety_trip_count   (health_safety_trip_count),
        .health_axis_stall_count    (health_axis_stall_count),
        .health_decoder_valid_count (health_decoder_valid_count),
        .health_telem_done_count    (health_telem_done_count)
    );

endmodule
