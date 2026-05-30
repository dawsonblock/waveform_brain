// waveform_brain_cdc_wrapper.v
//
// Centralized CDC wrapper for Waveform Brain.
//
// Purpose:
//   Keep AXI-clock control/status and fabric-clock processing crossings in one
//   explicit module. This avoids scattered ad-hoc CDC paths and makes Vivado
//   report_cdc review more deterministic.
//
// Assumptions:
//   - Multi-bit configuration changes are transferred with xpm_cdc_handshake.
//   - Command strobes are transferred with xpm_cdc_pulse.
//   - Monotonic fabric counters are transferred with xpm_cdc_gray.
//   - Telemetry window payload is transferred coherently with handshake.
//   - Single-bit status/control signals use xpm_cdc_single or array sync.
//
// This module is intended for Vivado/AMD-Xilinx flows where XPM_CDC primitives
// are available.

module waveform_brain_cdc_wrapper #(
    parameter int ADC_WIDTH   = 16,
    parameter int SCALE_WIDTH = 32
)(
    input  logic                         axi_clk,
    input  logic                         axi_rst_n,
    input  logic                         fabric_clk,
    input  logic                         fabric_rst_n,

    // ---------------------------------------------------------------------
    // AXI -> Fabric configuration/control
    // ---------------------------------------------------------------------
    input  logic                         axi_cfg_update,
    output logic                         axi_cfg_ack,

    input  logic                         axi_prbs_enable,
    input  logic signed [SCALE_WIDTH-1:0] axi_inv_delta_q,
    input  logic signed [SCALE_WIDTH-1:0] axi_delta_adc_q,
    input  logic signed [31:0]           axi_coeffs [0:3],
    input  logic [15:0]                  axi_alpha,
    input  logic [ADC_WIDTH-1:0]         axi_kill_threshold,
    input  logic [31:0]                  axi_telem_window_cycles,

    input  logic                         axi_clear_faults_pulse,
    input  logic                         axi_telem_start_pulse,
    input  logic                         axi_telem_clear_pulse,

    output logic                         fab_prbs_enable,
    output logic signed [SCALE_WIDTH-1:0] fab_inv_delta_q,
    output logic signed [SCALE_WIDTH-1:0] fab_delta_adc_q,
    output logic signed [31:0]           fab_coeffs [0:3],
    output logic [15:0]                  fab_alpha,
    output logic [ADC_WIDTH-1:0]         fab_kill_threshold,
    output logic [31:0]                  fab_telem_window_cycles,

    output logic                         fab_clear_faults_pulse,
    output logic                         fab_telem_start_pulse,
    output logic                         fab_telem_clear_pulse,

    // ---------------------------------------------------------------------
    // Fabric -> AXI status/telemetry/health
    // ---------------------------------------------------------------------
    input  logic                         fab_safety_kill,
    input  logic [15:0]                  fab_fault_flags,
    input  logic [15:0]                  fab_status_word,

    input  logic [31:0]                  fab_telem_flips_delta,
    input  logic [31:0]                  fab_telem_total_flips,
    input  logic                         fab_telem_sample_active,
    input  logic                         fab_telem_sample_done,

    input  logic [31:0]                  fab_health_status,
    input  logic [31:0]                  fab_health_safety_trip_count,
    input  logic [31:0]                  fab_health_axis_stall_count,
    input  logic [31:0]                  fab_health_decoder_valid_count,
    input  logic [31:0]                  fab_health_telem_done_count,

    input  logic [4:0]                   fab_axis_fifo_level,
    input  logic [31:0]                  fab_axis_fifo_overflow_count,
    input  logic [31:0]                  fab_axis_fifo_stall_count,
    input  logic [31:0]                  fab_axis_frame_drop_count,
    input  logic [31:0]                  fab_axis_sequence_count,

    output logic                         axi_safety_kill,
    output logic [15:0]                  axi_fault_flags,
    output logic [15:0]                  axi_status_word,

    output logic [31:0]                  axi_telem_flips_delta,
    output logic [31:0]                  axi_telem_total_flips,
    output logic                         axi_telem_sample_active,
    output logic                         axi_telem_sample_done,

    output logic [31:0]                  axi_health_status,
    output logic [31:0]                  axi_health_safety_trip_count,
    output logic [31:0]                  axi_health_axis_stall_count,
    output logic [31:0]                  axi_health_decoder_valid_count,
    output logic [31:0]                  axi_health_telem_done_count,

    output logic [4:0]                   axi_axis_fifo_level,
    output logic [31:0]                  axi_axis_fifo_overflow_count,
    output logic [31:0]                  axi_axis_fifo_stall_count,
    output logic [31:0]                  axi_axis_frame_drop_count,
    output logic [31:0]                  axi_axis_sequence_count
);

    localparam int CFG_WIDTH =
        1 + SCALE_WIDTH + SCALE_WIDTH + (4*32) + 16 + ADC_WIDTH + 32;

    // Pack configuration as a single coherent bus.
    logic [CFG_WIDTH-1:0] axi_cfg_bus;
    logic [CFG_WIDTH-1:0] fab_cfg_bus;
    logic                 fab_cfg_req;
    localparam int TELEM_WIDTH = 64;
    logic [TELEM_WIDTH-1:0] fab_telem_bus;
    logic [TELEM_WIDTH-1:0] axi_telem_bus;

    always @(*) begin
        axi_cfg_bus = {
            axi_prbs_enable,
            axi_inv_delta_q,
            axi_delta_adc_q,
            axi_coeffs[0],
            axi_coeffs[1],
            axi_coeffs[2],
            axi_coeffs[3],
            axi_alpha,
            axi_kill_threshold,
            axi_telem_window_cycles
        };

        // Cross telemetry window results coherently on sample_done.
        fab_telem_bus = {
            fab_telem_flips_delta,
            fab_telem_total_flips
        };
    end

    xpm_cdc_handshake #(
        .DEST_EXT_HSK   (0),
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .SIM_ASSERT_CHK (1),
        .SRC_SYNC_FF    (3),
        .WIDTH          (CFG_WIDTH)
    ) u_cfg_hs (
        .src_clk  (axi_clk),
        .src_in   (axi_cfg_bus),
        .src_send (axi_cfg_update),
        .src_rcv  (axi_cfg_ack),
        .dest_clk (fabric_clk),
        .dest_req (fab_cfg_req),
        .dest_ack (),
        .dest_out (fab_cfg_bus)
    );

    // Unpack only when the handshake delivers a coherent update. This avoids
    // fabric seeing a partially updated coefficient/parameter set.
    always_ff @(posedge fabric_clk or negedge fabric_rst_n) begin
        if (!fabric_rst_n) begin
            fab_prbs_enable         <= 1'b0;
            fab_inv_delta_q         <= 32'sh0001_0000;
            fab_delta_adc_q         <= 32'sh0001_0000;
            fab_coeffs[0]           <= 32'sh0;
            fab_coeffs[1]           <= 32'sh0;
            fab_coeffs[2]           <= 32'sh0;
            fab_coeffs[3]           <= 32'sh0;
            fab_alpha               <= 16'h0010;
            fab_kill_threshold      <= {ADC_WIDTH{1'b1}};
            fab_telem_window_cycles <= 32'd1000;
        end else if (fab_cfg_req) begin
            {
                fab_prbs_enable,
                fab_inv_delta_q,
                fab_delta_adc_q,
                fab_coeffs[0],
                fab_coeffs[1],
                fab_coeffs[2],
                fab_coeffs[3],
                fab_alpha,
                fab_kill_threshold,
                fab_telem_window_cycles
            } <= fab_cfg_bus;
        end
    end

    // AXI command pulses into fabric.
    xpm_cdc_pulse #(
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .REG_OUTPUT     (1),
        .RST_USED       (0),
        .SIM_ASSERT_CHK (1)
    ) u_clear_faults_pulse (
        .src_clk    (axi_clk),
        .src_pulse  (axi_clear_faults_pulse),
        .dest_clk   (fabric_clk),
        .dest_pulse (fab_clear_faults_pulse)
    );

    xpm_cdc_pulse #(
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .REG_OUTPUT     (1),
        .RST_USED       (0),
        .SIM_ASSERT_CHK (1)
    ) u_telem_start_pulse (
        .src_clk    (axi_clk),
        .src_pulse  (axi_telem_start_pulse),
        .dest_clk   (fabric_clk),
        .dest_pulse (fab_telem_start_pulse)
    );

    xpm_cdc_pulse #(
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .REG_OUTPUT     (1),
        .RST_USED       (0),
        .SIM_ASSERT_CHK (1)
    ) u_telem_clear_pulse (
        .src_clk    (axi_clk),
        .src_pulse  (axi_telem_clear_pulse),
        .dest_clk   (fabric_clk),
        .dest_pulse (fab_telem_clear_pulse)
    );

    // Single-bit status.
    xpm_cdc_single #(
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .SIM_ASSERT_CHK (1),
        .SRC_INPUT_REG  (1)
    ) u_safety_kill_single (
        .src_clk  (fabric_clk),
        .src_in   (fab_safety_kill),
        .dest_clk (axi_clk),
        .dest_out (axi_safety_kill)
    );

    xpm_cdc_single #(
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .SIM_ASSERT_CHK (1),
        .SRC_INPUT_REG  (1)
    ) u_telem_active_single (
        .src_clk  (fabric_clk),
        .src_in   (fab_telem_sample_active),
        .dest_clk (axi_clk),
        .dest_out (axi_telem_sample_active)
    );

    xpm_cdc_handshake #(
        .DEST_EXT_HSK   (0),
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .SIM_ASSERT_CHK (1),
        .SRC_SYNC_FF    (3),
        .WIDTH          (TELEM_WIDTH)
    ) u_telem_payload_hs (
        .src_clk  (fabric_clk),
        .src_in   (fab_telem_bus),
        .src_send (fab_telem_sample_done),
        .src_rcv  (),
        .dest_clk (axi_clk),
        .dest_req (axi_telem_sample_done),
        .dest_ack (),
        .dest_out (axi_telem_bus)
    );

    assign {
        axi_telem_flips_delta,
        axi_telem_total_flips
    } = axi_telem_bus;

    // Status bitfields. These are treated as diagnostic snapshots. Multi-bit
    // counters below use gray synchronizers.
    xpm_cdc_array_single #(
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .SIM_ASSERT_CHK (1),
        .SRC_INPUT_REG  (1),
        .WIDTH          (16)
    ) u_fault_flags_array (
        .src_clk  (fabric_clk),
        .src_in   (fab_fault_flags),
        .dest_clk (axi_clk),
        .dest_out (axi_fault_flags)
    );

    xpm_cdc_array_single #(
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .SIM_ASSERT_CHK (1),
        .SRC_INPUT_REG  (1),
        .WIDTH          (16)
    ) u_status_word_array (
        .src_clk  (fabric_clk),
        .src_in   (fab_status_word),
        .dest_clk (axi_clk),
        .dest_out (axi_status_word)
    );

    xpm_cdc_array_single #(
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .SIM_ASSERT_CHK (1),
        .SRC_INPUT_REG  (1),
        .WIDTH          (32)
    ) u_health_status_array (
        .src_clk  (fabric_clk),
        .src_in   (fab_health_status),
        .dest_clk (axi_clk),
        .dest_out (axi_health_status)
    );

    xpm_cdc_array_single #(
        .DEST_SYNC_FF   (3),
        .INIT_SYNC_FF   (0),
        .SIM_ASSERT_CHK (1),
        .SRC_INPUT_REG  (1),
        .WIDTH          (5)
    ) u_axis_fifo_level_array (
        .src_clk  (fabric_clk),
        .src_in   (fab_axis_fifo_level),
        .dest_clk (axi_clk),
        .dest_out (axi_axis_fifo_level)
    );

    // Fabric counters into AXI with xpm_cdc_gray.

    xpm_cdc_gray #(.DEST_SYNC_FF(3), .INIT_SYNC_FF(0), .REG_OUTPUT(1), .SIM_ASSERT_CHK(1), .WIDTH(32))
    u_health_safety_trip_gray (
        .src_clk      (fabric_clk),
        .src_in_bin   (fab_health_safety_trip_count),
        .dest_clk     (axi_clk),
        .dest_out_bin (axi_health_safety_trip_count)
    );

    xpm_cdc_gray #(.DEST_SYNC_FF(3), .INIT_SYNC_FF(0), .REG_OUTPUT(1), .SIM_ASSERT_CHK(1), .WIDTH(32))
    u_health_axis_stall_gray (
        .src_clk      (fabric_clk),
        .src_in_bin   (fab_health_axis_stall_count),
        .dest_clk     (axi_clk),
        .dest_out_bin (axi_health_axis_stall_count)
    );

    xpm_cdc_gray #(.DEST_SYNC_FF(3), .INIT_SYNC_FF(0), .REG_OUTPUT(1), .SIM_ASSERT_CHK(1), .WIDTH(32))
    u_health_decoder_valid_gray (
        .src_clk      (fabric_clk),
        .src_in_bin   (fab_health_decoder_valid_count),
        .dest_clk     (axi_clk),
        .dest_out_bin (axi_health_decoder_valid_count)
    );

    xpm_cdc_gray #(.DEST_SYNC_FF(3), .INIT_SYNC_FF(0), .REG_OUTPUT(1), .SIM_ASSERT_CHK(1), .WIDTH(32))
    u_health_telem_done_gray (
        .src_clk      (fabric_clk),
        .src_in_bin   (fab_health_telem_done_count),
        .dest_clk     (axi_clk),
        .dest_out_bin (axi_health_telem_done_count)
    );

    xpm_cdc_gray #(.DEST_SYNC_FF(3), .INIT_SYNC_FF(0), .REG_OUTPUT(1), .SIM_ASSERT_CHK(1), .WIDTH(32))
    u_axis_fifo_overflow_gray (
        .src_clk      (fabric_clk),
        .src_in_bin   (fab_axis_fifo_overflow_count),
        .dest_clk     (axi_clk),
        .dest_out_bin (axi_axis_fifo_overflow_count)
    );

    xpm_cdc_gray #(.DEST_SYNC_FF(3), .INIT_SYNC_FF(0), .REG_OUTPUT(1), .SIM_ASSERT_CHK(1), .WIDTH(32))
    u_axis_fifo_stall_gray (
        .src_clk      (fabric_clk),
        .src_in_bin   (fab_axis_fifo_stall_count),
        .dest_clk     (axi_clk),
        .dest_out_bin (axi_axis_fifo_stall_count)
    );

    xpm_cdc_gray #(.DEST_SYNC_FF(3), .INIT_SYNC_FF(0), .REG_OUTPUT(1), .SIM_ASSERT_CHK(1), .WIDTH(32))
    u_axis_frame_drop_gray (
        .src_clk      (fabric_clk),
        .src_in_bin   (fab_axis_frame_drop_count),
        .dest_clk     (axi_clk),
        .dest_out_bin (axi_axis_frame_drop_count)
    );

    xpm_cdc_gray #(.DEST_SYNC_FF(3), .INIT_SYNC_FF(0), .REG_OUTPUT(1), .SIM_ASSERT_CHK(1), .WIDTH(32))
    u_axis_sequence_gray (
        .src_clk      (fabric_clk),
        .src_in_bin   (fab_axis_sequence_count),
        .dest_clk     (axi_clk),
        .dest_out_bin (axi_axis_sequence_count)
    );

endmodule
