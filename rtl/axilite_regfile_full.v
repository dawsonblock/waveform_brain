`timescale 1ns/1ps

// axilite_regfile_full.v
//
// Standards-oriented AXI4-Lite register file for Waveform Brain v1.0.
//
// This module exposes a fuller AXI4-Lite slave interface than the lightweight
// scaffold register file. It includes independent AW/W capture, BREADY/RREADY,
// and 2-bit BRESP/RRESP signals.
//
// It is provided as an optional integration target. The existing
// axilite_regfile.v remains available for the lightweight scaffold path.


module axilite_regfile_full (
module axilite_regfile_full (
    input  logic                         s_axi_aclk,
    input  logic                         s_axi_aresetn,

    // AXI4-Lite write address channel
    input  logic [7:0]                   s_axi_awaddr,
    input  logic                         s_axi_awvalid,
    output logic                         s_axi_awready,

    // AXI4-Lite write data channel
    input  logic [31:0]                  s_axi_wdata,
    input  logic [3:0]                   s_axi_wstrb,
    input  logic                         s_axi_wvalid,
    output logic                         s_axi_wready,

    // AXI4-Lite write response channel
    output logic [1:0]                   s_axi_bresp,
    output logic                         s_axi_bvalid,
    input  logic                         s_axi_bready,

    // AXI4-Lite read address channel
    input  logic [7:0]                   s_axi_araddr,
    input  logic                         s_axi_arvalid,
    output logic                         s_axi_arready,

    // AXI4-Lite read data channel
    output logic [31:0]                  s_axi_rdata,
    output logic [1:0]                   s_axi_rresp,
    output logic                         s_axi_rvalid,
    input  logic                         s_axi_rready,

    // Control outputs
    output logic                         prbs_enable,
    output logic signed [31:0]           inv_delta_q,
    output logic signed [31:0]           delta_adc_q,
    output logic signed [31:0]           coeffs [0:3],
    output logic [15:0]                  alpha,
    output logic [15:0]                  kill_threshold,
    output logic                         clear_faults,

    input  logic [15:0]                  status_word_in,
    input  logic [15:0]                  fault_flags_in,
    input  logic [31:0]                  build_id,

    // Telemetry signals from fabric
    input  logic [31:0]                  telemetry_flips_delta_in,
    input  logic [31:0]                  telemetry_total_flips_in,
    input  logic                         telemetry_sample_active_in,
    input  logic                         telemetry_sample_done_in,

    // Health monitor signals from fabric
    input  logic [31:0]                  health_status_in,
    input  logic [31:0]                  health_safety_trip_count_in,
    input  logic [31:0]                  health_axis_stall_count_in,
    input  logic [31:0]                  health_decoder_valid_count_in,
    input  logic [31:0]                  health_telem_done_count_in,

    // AXI-Stream packet/FIFO diagnostics from fabric
    input  logic [4:0]                   axis_fifo_level_in,
    input  logic [31:0]                  axis_fifo_overflow_count_in,
    input  logic [31:0]                  axis_fifo_stall_count_in,
    input  logic [31:0]                  axis_frame_drop_count_in,
    input  logic [31:0]                  axis_sequence_count_in,

    // Telemetry control outputs
    output logic                         telem_start_sample,
    output logic                         telem_clear_total,
    output logic [31:0]                  telem_window_cycles,

    // Pulses high for one AXI clock when a coherent configuration register changes.
    // Used by waveform_brain_cdc_wrapper to handshake multi-bit config into fabric.
    output logic                         cfg_update_pulse
);

    localparam logic [1:0] AXI_RESP_OKAY   = 2'b00;
    localparam logic [1:0] AXI_RESP_SLVERR = 2'b10;

    // Register storage
    logic [31:0] reg_build_id;
    logic [15:0] reg_status;
    logic [15:0] reg_faults;

    logic        reg_prbs_enable;
    logic [31:0] reg_inv_delta_q;
    logic [31:0] reg_delta_adc_q;
    logic [31:0] reg_coeff0;
    logic [31:0] reg_coeff1;
    logic [31:0] reg_coeff2;
    logic [31:0] reg_coeff3;
    logic [15:0] reg_alpha;
    logic [15:0] reg_kill_threshold;
    logic [31:0] reg_telem_window;

    // Shadow configuration registers are software-visible staging values.
    // Active registers above are committed to fabric only when CFG_APPLY is written.
    logic        shd_prbs_enable;
    logic [31:0] shd_inv_delta_q;
    logic [31:0] shd_delta_adc_q;
    logic [31:0] shd_coeff0;
    logic [31:0] shd_coeff1;
    logic [31:0] shd_coeff2;
    logic [31:0] shd_coeff3;
    logic [15:0] shd_alpha;
    logic [15:0] shd_kill_threshold;
    logic [31:0] shd_telem_window;

    // One-cycle command pulses
    logic clear_faults_pulse;
    logic telem_start_pulse;
    logic telem_clear_pulse;

    // Write channel holding registers. AXI4-Lite permits AW and W to arrive
    // independently, so capture them separately and execute once both are held.
    logic        aw_holding;
    logic        w_holding;
    logic [7:0]  awaddr_q;
    logic [31:0] wdata_q;
    logic [3:0]  wstrb_q;
    logic [31:0] applied_value;

    // Byte-enable helper.
    function automatic [31:0] apply_wstrb(
        input [31:0] old_value,
        input [31:0] new_value,
        input [3:0]  strobe
    );
        automatic logic [31:0] result;
        begin
            result = old_value;
            if (strobe[0]) result[7:0]   = new_value[7:0];
            if (strobe[1]) result[15:8]  = new_value[15:8];
            if (strobe[2]) result[23:16] = new_value[23:16];
            if (strobe[3]) result[31:24] = new_value[31:24];
            apply_wstrb = result;
        end
    endfunction

    function automatic [31:0] read_mux(input [7:0] addr);
        begin
            unique case (addr)
                8'h00: read_mux = reg_build_id;
                8'h04: read_mux = {16'h0, reg_status};
                8'h08: read_mux = {16'h0, reg_faults};
                8'h0C: read_mux = {31'h0, reg_prbs_enable};
                8'h10: read_mux = shd_inv_delta_q;
                8'h14: read_mux = shd_delta_adc_q;
                8'h18: read_mux = shd_coeff0;
                8'h1C: read_mux = shd_coeff1;
                8'h20: read_mux = shd_coeff2;
                8'h24: read_mux = shd_coeff3;
                8'h28: read_mux = {16'h0, shd_alpha};
                8'h2C: read_mux = {16'h0, shd_kill_threshold};
                8'h30: read_mux = 32'h0; // command strobe
                8'h34: read_mux = 32'h0; // command strobe
                8'h38: read_mux = shd_telem_window;
                8'h3C: read_mux = {30'h0, telemetry_sample_active_in, telemetry_sample_done_in};
                8'h40: read_mux = telemetry_flips_delta_in;
                8'h44: read_mux = telemetry_total_flips_in;
                8'h48: read_mux = health_status_in;
                8'h4C: read_mux = health_safety_trip_count_in;
                8'h50: read_mux = health_axis_stall_count_in;
                8'h54: read_mux = health_decoder_valid_count_in;
                8'h58: read_mux = health_telem_done_count_in;
                8'h5C: read_mux = {27'd0, axis_fifo_level_in};
                8'h60: read_mux = axis_fifo_overflow_count_in;
                8'h64: read_mux = axis_fifo_stall_count_in;
                8'h68: read_mux = axis_frame_drop_count_in;
                8'h6C: read_mux = axis_sequence_count_in;
                8'h70: read_mux = 32'h0; // command strobe
                default: read_mux = 32'hDEAD_BEEF;
            endcase
        end
    endfunction

    function automatic logic valid_addr(input [7:0] addr);
        begin
            unique case (addr)
                8'h00, 8'h04, 8'h08, 8'h0C, 8'h10, 8'h14, 8'h18, 8'h1C,
                8'h20, 8'h24, 8'h28, 8'h2C, 8'h30, 8'h34, 8'h38, 8'h3C,
                8'h40, 8'h44, 8'h48, 8'h4C, 8'h50, 8'h54, 8'h58,
                8'h5C, 8'h60, 8'h64, 8'h68, 8'h6C, 8'h70:
                    valid_addr = 1'b1;
                default:
                    valid_addr = 1'b0;
            endcase
        end
    endfunction

    always_ff @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn) begin
            reg_build_id          <= 32'h5742_5631; // "WBV1"
            reg_status            <= 16'h0;
            reg_faults            <= 16'h0;
            reg_prbs_enable       <= 1'b0;
            reg_inv_delta_q       <= 32'h0001_0000;
            reg_delta_adc_q       <= 32'h0001_0000;
            reg_coeff0            <= 32'h0;
            reg_coeff1            <= 32'h0;
            reg_coeff2            <= 32'h0;
            reg_coeff3            <= 32'h0;
            reg_alpha             <= 16'h0010;
            reg_kill_threshold    <= 16'h7FFF;
            reg_telem_window      <= 32'd1000;

            shd_prbs_enable       <= 1'b0;
            shd_inv_delta_q       <= 32'h0001_0000;
            shd_delta_adc_q       <= 32'h0001_0000;
            shd_coeff0            <= 32'h0;
            shd_coeff1            <= 32'h0;
            shd_coeff2            <= 32'h0;
            shd_coeff3            <= 32'h0;
            shd_alpha             <= 16'h0010;
            shd_kill_threshold    <= 16'h7FFF;
            shd_telem_window      <= 32'd1000;

            clear_faults_pulse    <= 1'b0;
            telem_start_pulse     <= 1'b0;
            telem_clear_pulse     <= 1'b0;
            cfg_update_pulse      <= 1'b0;

            aw_holding            <= 1'b0;
            w_holding             <= 1'b0;
            awaddr_q              <= 8'h00;
            wdata_q               <= 32'h0;
            wstrb_q               <= 4'h0;

            s_axi_awready         <= 1'b0;
            s_axi_wready          <= 1'b0;
            s_axi_bresp           <= AXI_RESP_OKAY;
            s_axi_bvalid          <= 1'b0;
            s_axi_arready         <= 1'b0;
            s_axi_rdata           <= 32'h0;
            s_axi_rresp           <= AXI_RESP_OKAY;
            s_axi_rvalid          <= 1'b0;
        end else begin
            // Default pulse outputs.
            clear_faults_pulse <= 1'b0;
            telem_start_pulse  <= 1'b0;
            telem_clear_pulse  <= 1'b0;
            cfg_update_pulse   <= 1'b0;

            // Sample fabric status into AXI clock domain. If this clock differs
            // from fabric, external CDC wrappers are still required.
            reg_build_id <= build_id;
            reg_status   <= status_word_in;
            reg_faults   <= fault_flags_in;

            // Default ready signals low unless accepting.
            s_axi_awready <= 1'b0;
            s_axi_wready  <= 1'b0;
            s_axi_arready <= 1'b0;

            // Accept write address when not already holding one and response
            // channel is not backpressured.
            if (!aw_holding && !s_axi_bvalid && s_axi_awvalid) begin
                awaddr_q      <= s_axi_awaddr;
                aw_holding    <= 1'b1;
                s_axi_awready <= 1'b1;
            end

            // Accept write data independently.
            if (!w_holding && !s_axi_bvalid && s_axi_wvalid) begin
                wdata_q      <= s_axi_wdata;
                wstrb_q      <= s_axi_wstrb;
                w_holding    <= 1'b1;
                s_axi_wready <= 1'b1;
            end

            // Execute write once both channels are captured.
            if (aw_holding && w_holding && !s_axi_bvalid) begin
                s_axi_bresp  <= valid_addr(awaddr_q) ? AXI_RESP_OKAY : AXI_RESP_SLVERR;
                s_axi_bvalid <= 1'b1;

                unique case (awaddr_q)
                    8'h0C: begin
                        applied_value = apply_wstrb(
                            {31'h0, shd_prbs_enable},
                            wdata_q,
                            wstrb_q
                        );
                        shd_prbs_enable <= applied_value[0];
                    end
                    8'h10: begin
                        shd_inv_delta_q <= apply_wstrb(shd_inv_delta_q, wdata_q, wstrb_q);
                    end
                    8'h14: begin
                        shd_delta_adc_q <= apply_wstrb(shd_delta_adc_q, wdata_q, wstrb_q);
                    end
                    8'h18: begin
                        shd_coeff0 <= apply_wstrb(shd_coeff0, wdata_q, wstrb_q);
                    end
                    8'h1C: begin
                        shd_coeff1 <= apply_wstrb(shd_coeff1, wdata_q, wstrb_q);
                    end
                    8'h20: begin
                        shd_coeff2 <= apply_wstrb(shd_coeff2, wdata_q, wstrb_q);
                    end
                    8'h24: begin
                        shd_coeff3 <= apply_wstrb(shd_coeff3, wdata_q, wstrb_q);
                    end
                    8'h28: begin
                        applied_value = apply_wstrb(
                            {16'h0, shd_alpha},
                            wdata_q,
                            wstrb_q
                        );
                        shd_alpha <= applied_value[15:0];
                    end
                    8'h2C: begin
                        applied_value = apply_wstrb(
                            {16'h0, shd_kill_threshold},
                            wdata_q,
                            wstrb_q
                        );
                        shd_kill_threshold <= applied_value[15:0];
                    end
                    8'h30: clear_faults_pulse <= wdata_q[0];
                    8'h34: begin
                        telem_start_pulse <= wdata_q[0];
                        telem_clear_pulse <= wdata_q[1];
                    end
                    8'h38: begin
                        shd_telem_window <= apply_wstrb(shd_telem_window, wdata_q, wstrb_q);
                    end
                    8'h70: begin
                        applied_value = apply_wstrb(32'h0, wdata_q, wstrb_q);
                        if (applied_value[0]) begin
                            reg_prbs_enable    <= shd_prbs_enable;
                            reg_inv_delta_q    <= shd_inv_delta_q;
                            reg_delta_adc_q    <= shd_delta_adc_q;
                            reg_coeff0         <= shd_coeff0;
                            reg_coeff1         <= shd_coeff1;
                            reg_coeff2         <= shd_coeff2;
                            reg_coeff3         <= shd_coeff3;
                            reg_alpha          <= shd_alpha;
                            reg_kill_threshold <= shd_kill_threshold;
                            reg_telem_window   <= shd_telem_window;
                            cfg_update_pulse   <= 1'b1;
                        end
                    end
                    default: ;
                endcase

                aw_holding <= 1'b0;
                w_holding  <= 1'b0;
            end

            // Complete write response.
            if (s_axi_bvalid && s_axi_bready) begin
                s_axi_bvalid <= 1'b0;
            end

            // Accept read only when no read response is outstanding.
            if (!s_axi_rvalid && s_axi_arvalid) begin
                s_axi_arready <= 1'b1;
                s_axi_rdata   <= read_mux(s_axi_araddr);
                s_axi_rresp   <= valid_addr(s_axi_araddr) ? AXI_RESP_OKAY : AXI_RESP_SLVERR;
                s_axi_rvalid  <= 1'b1;
            end

            // Complete read response.
            if (s_axi_rvalid && s_axi_rready) begin
                s_axi_rvalid <= 1'b0;
            end
        end
    end

    assign prbs_enable         = reg_prbs_enable;
    assign inv_delta_q         = reg_inv_delta_q;
    assign delta_adc_q         = reg_delta_adc_q;
    assign coeffs[0]           = reg_coeff0;
    assign coeffs[1]           = reg_coeff1;
    assign coeffs[2]           = reg_coeff2;
    assign coeffs[3]           = reg_coeff3;
    assign alpha               = reg_alpha;
    assign kill_threshold      = reg_kill_threshold;
    assign clear_faults        = clear_faults_pulse;
    assign telem_start_sample  = telem_start_pulse;
    assign telem_clear_total   = telem_clear_pulse;
    assign telem_window_cycles = reg_telem_window;

endmodule
