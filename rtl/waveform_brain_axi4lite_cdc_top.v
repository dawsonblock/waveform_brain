// waveform_brain_axi4lite_cdc_top.v
//
// Preferred CDC-hardened top-level wrapper.
//
// This top separates AXI-Lite clocking from the fabric processing clock and
// places all control/status crossings through waveform_brain_cdc_wrapper.v.

module waveform_brain_axi4lite_cdc_top #(
    parameter int ADC_WIDTH   = 16,
    parameter int SCALE_WIDTH = 32
)(
    input  logic                         s_axi_aclk,
    input  logic                         s_axi_aresetn,
    input  logic                         fabric_clk,
    input  logic                         fabric_rst_n,

    input  logic signed [ADC_WIDTH-1:0]  adc_in [0:3],

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

    output logic [63:0]                  m_axis_tdata,
    output logic                         m_axis_tvalid,
    input  logic                         m_axis_tready,
    output logic                         m_axis_tlast,

    output logic                         safety_kill
);

    // AXI-domain control/status wires.
    logic prbs_enable_axi;
    logic signed [SCALE_WIDTH-1:0] inv_delta_q_axi;
    logic signed [SCALE_WIDTH-1:0] delta_adc_q_axi;
    logic signed [31:0] coeffs_axi [0:3];
    logic [15:0] alpha_axi;
    logic [ADC_WIDTH-1:0] kill_threshold_axi;
    logic clear_faults_axi;
    logic cfg_update_axi;
    logic cfg_ack_axi;

    logic [15:0] fault_flags_axi;
    logic [15:0] status_word_axi;

    logic [31:0] telem_flips_delta_axi;
    logic [31:0] telem_total_flips_axi;
    logic        telem_sample_active_axi;
    logic        telem_sample_done_axi;
    logic        telem_start_sample_axi;
    logic        telem_clear_total_axi;
    logic [31:0] telem_window_cycles_axi;

    logic [31:0] health_status_axi;
    logic [31:0] health_safety_trip_count_axi;
    logic [31:0] health_axis_stall_count_axi;
    logic [31:0] health_decoder_valid_count_axi;
    logic [31:0] health_telem_done_count_axi;

    logic [4:0]  axis_fifo_level_axi;
    logic [31:0] axis_fifo_overflow_count_axi;
    logic [31:0] axis_fifo_stall_count_axi;
    logic [31:0] axis_frame_drop_count_axi;
    logic [31:0] axis_sequence_count_axi;

    // Fabric-domain wires.
    logic prbs_enable_fab;
    logic signed [SCALE_WIDTH-1:0] inv_delta_q_fab;
    logic signed [SCALE_WIDTH-1:0] delta_adc_q_fab;
    logic signed [31:0] coeffs_fab [0:3];
    logic [15:0] alpha_fab;
    logic [ADC_WIDTH-1:0] kill_threshold_fab;
    logic clear_faults_fab;

    logic [15:0] fault_flags_fab;
    logic [15:0] status_word_fab;

    logic [31:0] telem_flips_delta_fab;
    logic [31:0] telem_total_flips_fab;
    logic        telem_sample_active_fab;
    logic        telem_sample_done_fab;
    logic        telem_start_sample_fab;
    logic        telem_clear_total_fab;
    logic [31:0] telem_window_cycles_fab;

    logic [31:0] health_status_fab;
    logic [31:0] health_safety_trip_count_fab;
    logic [31:0] health_axis_stall_count_fab;
    logic [31:0] health_decoder_valid_count_fab;
    logic [31:0] health_telem_done_count_fab;

    logic [4:0]  axis_fifo_level_fab;
    logic [31:0] axis_fifo_overflow_count_fab;
    logic [31:0] axis_fifo_stall_count_fab;
    logic [31:0] axis_frame_drop_count_fab;
    logic [31:0] axis_sequence_count_fab;

    logic        safety_kill_fab;
    logic        safety_kill_axi;

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

        .prbs_enable                   (prbs_enable_axi),
        .inv_delta_q                   (inv_delta_q_axi),
        .delta_adc_q                   (delta_adc_q_axi),
        .coeffs                        (coeffs_axi),
        .alpha                         (alpha_axi),
        .kill_threshold                (kill_threshold_axi),
        .clear_faults                  (clear_faults_axi),

        .status_word_in                (status_word_axi),
        .fault_flags_in                (fault_flags_axi),
        .build_id                      (BUILD_ID),

        .telemetry_flips_delta_in      (telem_flips_delta_axi),
        .telemetry_total_flips_in      (telem_total_flips_axi),
        .telemetry_sample_active_in    (telem_sample_active_axi),
        .telemetry_sample_done_in      (telem_sample_done_axi),

        .health_status_in              (health_status_axi),
        .health_safety_trip_count_in   (health_safety_trip_count_axi),
        .health_axis_stall_count_in    (health_axis_stall_count_axi),
        .health_decoder_valid_count_in (health_decoder_valid_count_axi),
        .health_telem_done_count_in    (health_telem_done_count_axi),

        .axis_fifo_level_in            (axis_fifo_level_axi),
        .axis_fifo_overflow_count_in   (axis_fifo_overflow_count_axi),
        .axis_fifo_stall_count_in      (axis_fifo_stall_count_axi),
        .axis_frame_drop_count_in      (axis_frame_drop_count_axi),
        .axis_sequence_count_in        (axis_sequence_count_axi),

        .telem_start_sample            (telem_start_sample_axi),
        .telem_clear_total             (telem_clear_total_axi),
        .telem_window_cycles           (telem_window_cycles_axi),
        .cfg_update_pulse              (cfg_update_axi)
    );

    waveform_brain_cdc_wrapper #(
        .ADC_WIDTH   (ADC_WIDTH),
        .SCALE_WIDTH (SCALE_WIDTH)
    ) u_cdc (
        .axi_clk                       (s_axi_aclk),
        .axi_rst_n                     (s_axi_aresetn),
        .fabric_clk                    (fabric_clk),
        .fabric_rst_n                  (fabric_rst_n),

        .axi_cfg_update                (cfg_update_axi),
        .axi_cfg_ack                   (cfg_ack_axi),
        .axi_prbs_enable               (prbs_enable_axi),
        .axi_inv_delta_q               (inv_delta_q_axi),
        .axi_delta_adc_q               (delta_adc_q_axi),
        .axi_coeffs                    (coeffs_axi),
        .axi_alpha                     (alpha_axi),
        .axi_kill_threshold            (kill_threshold_axi),
        .axi_telem_window_cycles       (telem_window_cycles_axi),
        .axi_clear_faults_pulse        (clear_faults_axi),
        .axi_telem_start_pulse         (telem_start_sample_axi),
        .axi_telem_clear_pulse         (telem_clear_total_axi),

        .fab_prbs_enable               (prbs_enable_fab),
        .fab_inv_delta_q               (inv_delta_q_fab),
        .fab_delta_adc_q               (delta_adc_q_fab),
        .fab_coeffs                    (coeffs_fab),
        .fab_alpha                     (alpha_fab),
        .fab_kill_threshold            (kill_threshold_fab),
        .fab_telem_window_cycles       (telem_window_cycles_fab),
        .fab_clear_faults_pulse        (clear_faults_fab),
        .fab_telem_start_pulse         (telem_start_sample_fab),
        .fab_telem_clear_pulse         (telem_clear_total_fab),

        .fab_safety_kill               (safety_kill_fab),
        .fab_fault_flags               (fault_flags_fab),
        .fab_status_word               (status_word_fab),
        .fab_telem_flips_delta         (telem_flips_delta_fab),
        .fab_telem_total_flips         (telem_total_flips_fab),
        .fab_telem_sample_active       (telem_sample_active_fab),
        .fab_telem_sample_done         (telem_sample_done_fab),
        .fab_health_status             (health_status_fab),
        .fab_health_safety_trip_count  (health_safety_trip_count_fab),
        .fab_health_axis_stall_count   (health_axis_stall_count_fab),
        .fab_health_decoder_valid_count(health_decoder_valid_count_fab),
        .fab_health_telem_done_count   (health_telem_done_count_fab),

        .fab_axis_fifo_level           (axis_fifo_level_fab),
        .fab_axis_fifo_overflow_count  (axis_fifo_overflow_count_fab),
        .fab_axis_fifo_stall_count     (axis_fifo_stall_count_fab),
        .fab_axis_frame_drop_count     (axis_frame_drop_count_fab),
        .fab_axis_sequence_count       (axis_sequence_count_fab),

        .axi_safety_kill               (safety_kill_axi),
        .axi_fault_flags               (fault_flags_axi),
        .axi_status_word               (status_word_axi),
        .axi_telem_flips_delta         (telem_flips_delta_axi),
        .axi_telem_total_flips         (telem_total_flips_axi),
        .axi_telem_sample_active       (telem_sample_active_axi),
        .axi_telem_sample_done         (telem_sample_done_axi),
        .axi_health_status             (health_status_axi),
        .axi_health_safety_trip_count  (health_safety_trip_count_axi),
        .axi_health_axis_stall_count   (health_axis_stall_count_axi),
        .axi_health_decoder_valid_count(health_decoder_valid_count_axi),
        .axi_health_telem_done_count   (health_telem_done_count_axi),

        .axi_axis_fifo_level           (axis_fifo_level_axi),
        .axi_axis_fifo_overflow_count  (axis_fifo_overflow_count_axi),
        .axi_axis_fifo_stall_count     (axis_fifo_stall_count_axi),
        .axi_axis_frame_drop_count     (axis_frame_drop_count_axi),
        .axi_axis_sequence_count       (axis_sequence_count_axi)
    );

    waveform_control_4q_top #(
        .ADC_WIDTH   (ADC_WIDTH),
        .SCALE_WIDTH (SCALE_WIDTH)
    ) u_core (
        .clk                        (fabric_clk),
        .rst_n                      (fabric_rst_n),
        .adc_in                     (adc_in),
        .prbs_enable                (prbs_enable_fab),
        .inv_delta_q                (inv_delta_q_fab),
        .delta_adc_q                (delta_adc_q_fab),
        .coeffs                     (coeffs_fab),
        .alpha                      (alpha_fab),
        .kill_threshold             (kill_threshold_fab),
        .clear_faults               (clear_faults_fab),
        .telem_start_sample         (telem_start_sample_fab),
        .telem_clear_total          (telem_clear_total_fab),
        .telem_window_cycles        (telem_window_cycles_fab),
        .m_axis_tdata               (m_axis_tdata),
        .m_axis_tvalid              (m_axis_tvalid),
        .m_axis_tready              (m_axis_tready),
        .m_axis_tlast               (m_axis_tlast),
        .safety_kill                (safety_kill_fab),
        .fault_flags                (fault_flags_fab),
        .status_word                (status_word_fab),
        .telem_flips_delta          (telem_flips_delta_fab),
        .telem_total_flips          (telem_total_flips_fab),
        .telem_sample_active        (telem_sample_active_fab),
        .telem_sample_done          (telem_sample_done_fab),
        .health_status              (health_status_fab),
        .health_safety_trip_count   (health_safety_trip_count_fab),
        .health_axis_stall_count    (health_axis_stall_count_fab),
        .health_decoder_valid_count (health_decoder_valid_count_fab),
        .health_telem_done_count    (health_telem_done_count_fab),
        .axis_fifo_level            (axis_fifo_level_fab),
        .axis_fifo_overflow_count   (axis_fifo_overflow_count_fab),
        .axis_fifo_stall_count      (axis_fifo_stall_count_fab),
        .axis_frame_drop_count      (axis_frame_drop_count_fab),
        .axis_sequence_count        (axis_sequence_count_fab)
    );

    assign safety_kill = safety_kill_fab;

endmodule
