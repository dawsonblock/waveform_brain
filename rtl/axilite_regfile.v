// axilite_regfile.v
//
// AXI-Lite-style register file for Waveform Brain v1.0.
//
// v0.11 hardening:
//   - Replaces the old combinational/single-cycle ready-valid behavior.
//   - Separates write address/data capture from register writes.
//   - Separates read address capture from read-data response.
//   - Produces one-cycle AWREADY/WREADY/ARREADY accept pulses.
//   - Holds BVALID/RVALID until the corresponding transaction is considered complete.
//   - Generates pulse-style control bits for CLEAR_FAULTS and telemetry controls.
//
// Note:
//   This scaffold interface intentionally remains lightweight and does not expose
//   BREADY/RREADY/RRESP. A fully standards-complete AXI4-Lite slave should add
//   BREADY/RREADY and 2-bit BRESP/RRESP, or use the Xilinx AXI-Lite template/IP.
//   Within the existing project interface, this is a deterministic handshake
//   upgrade over the old always-ready combinational model.

module axilite_regfile (
    input  logic         clk,
    input  logic         rst_n,

    // AXI-Lite-style interface used by this scaffold
    input  logic         awvalid,
    input  logic  [7:0]  awaddr,
    input  logic [31:0]  wdata,
    input  logic [3:0]   wstrb,
    input  logic         wvalid,
    input  logic         arvalid,
    input  logic  [7:0]  araddr,
    output logic [31:0]  rdata,
    output logic         rvalid,
    output logic         awready,
    output logic         wready,
    output logic         arready,
    output logic         bvalid,
    output logic         bresp,

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

    // Telemetry signals from top level
    input  logic [31:0]                  telemetry_flips_delta_in,
    input  logic [31:0]                  telemetry_total_flips_in,
    input  logic                         telemetry_sample_active_in,
    input  logic                         telemetry_sample_done_in,

    // Health monitor inputs from top level
    input  logic [31:0]                  health_status_in,
    input  logic [31:0]                  health_safety_trip_count_in,
    input  logic [31:0]                  health_axis_stall_count_in,
    input  logic [31:0]                  health_decoder_valid_count_in,
    input  logic [31:0]                  health_telem_done_count_in,

    // Telemetry control outputs to top level
    output logic                         telem_start_sample,
    output logic                         telem_clear_total,
    output logic [31:0]                  telem_window_cycles
);

    // ---------------------------------------------------------------------
    // Register storage
    // ---------------------------------------------------------------------
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

    // Pulse outputs. These are generated for one clk cycle on accepted writes.
    logic clear_faults_pulse;
    logic telem_start_pulse;
    logic telem_clear_pulse;

    // ---------------------------------------------------------------------
    // Lightweight write-channel state
    // ---------------------------------------------------------------------
    logic        write_busy;
    logic [7:0]  wr_addr_q;
    logic [31:0] wr_data_q;
    logic [3:0]  wr_strb_q;

    wire write_accept = awvalid && wvalid && !write_busy;

    // ---------------------------------------------------------------------
    // Lightweight read-channel state
    // ---------------------------------------------------------------------
    logic        read_busy;
    logic [7:0]  rd_addr_q;

    wire read_accept = arvalid && !read_busy;

    // Byte-enable write helper.
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

    // Read mux.
    function automatic [31:0] read_mux(input [7:0] addr);
        begin
            unique case (addr)
                8'h00: read_mux = reg_build_id;
                8'h04: read_mux = {16'h0, reg_status};
                8'h08: read_mux = {16'h0, reg_faults};
                8'h0C: read_mux = {31'h0, reg_prbs_enable};
                8'h10: read_mux = reg_inv_delta_q;
                8'h14: read_mux = reg_delta_adc_q;
                8'h18: read_mux = reg_coeff0;
                8'h1C: read_mux = reg_coeff1;
                8'h20: read_mux = reg_coeff2;
                8'h24: read_mux = reg_coeff3;
                8'h28: read_mux = {16'h0, reg_alpha};
                8'h2C: read_mux = {16'h0, reg_kill_threshold};
                8'h30: read_mux = 32'h0; // CLEAR_FAULTS is pulse-only
                8'h34: read_mux = 32'h0; // TELEM_CTRL is pulse-only
                8'h38: read_mux = reg_telem_window;
                8'h3C: read_mux = {30'h0, telemetry_sample_active_in, telemetry_sample_done_in};
                8'h40: read_mux = telemetry_flips_delta_in;
                8'h44: read_mux = telemetry_total_flips_in;
                8'h48: read_mux = health_status_in;
                8'h4C: read_mux = health_safety_trip_count_in;
                8'h50: read_mux = health_axis_stall_count_in;
                8'h54: read_mux = health_decoder_valid_count_in;
                8'h58: read_mux = health_telem_done_count_in;
                default: read_mux = 32'hDEAD_BEEF;
            endcase
        end
    endfunction

    // ---------------------------------------------------------------------
    // Main sequential control
    // ---------------------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
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

            wr_addr_q             <= 8'h00;
            wr_data_q             <= 32'h0;
            wr_strb_q             <= 4'h0;
            write_busy            <= 1'b0;

            rd_addr_q             <= 8'h00;
            read_busy             <= 1'b0;

            rdata                 <= 32'h0;
            rvalid                <= 1'b0;
            bvalid                <= 1'b0;
            bresp                 <= 1'b0;
            awready               <= 1'b0;
            wready                <= 1'b0;
            arready               <= 1'b0;

            clear_faults_pulse    <= 1'b0;
            telem_start_pulse     <= 1'b0;
            telem_clear_pulse     <= 1'b0;
        end else begin
            // Default pulse outputs low unless a write below asserts them.
            clear_faults_pulse <= 1'b0;
            telem_start_pulse  <= 1'b0;
            telem_clear_pulse  <= 1'b0;

            // Status is sampled synchronously into the AXI-Lite register domain.
            reg_build_id <= build_id;
            reg_status   <= status_word_in;
            reg_faults   <= fault_flags_in;

            // Ready pulses default low.
            awready <= 1'b0;
            wready  <= 1'b0;
            arready <= 1'b0;

            // Write accept: capture address/data together.
            if (write_accept) begin
                awready    <= 1'b1;
                wready     <= 1'b1;
                wr_addr_q  <= awaddr;
                wr_data_q  <= wdata;
                wr_strb_q  <= wstrb;
                write_busy <= 1'b1;
            end

            // Apply write on the cycle after accept.
            if (write_busy) begin
                unique case (wr_addr_q)
                    8'h0C: reg_prbs_enable    <= apply_wstrb({31'h0, reg_prbs_enable}, wr_data_q, wr_strb_q)[0];
                    8'h10: reg_inv_delta_q    <= apply_wstrb(reg_inv_delta_q, wr_data_q, wr_strb_q);
                    8'h14: reg_delta_adc_q    <= apply_wstrb(reg_delta_adc_q, wr_data_q, wr_strb_q);
                    8'h18: reg_coeff0         <= apply_wstrb(reg_coeff0, wr_data_q, wr_strb_q);
                    8'h1C: reg_coeff1         <= apply_wstrb(reg_coeff1, wr_data_q, wr_strb_q);
                    8'h20: reg_coeff2         <= apply_wstrb(reg_coeff2, wr_data_q, wr_strb_q);
                    8'h24: reg_coeff3         <= apply_wstrb(reg_coeff3, wr_data_q, wr_strb_q);
                    8'h28: reg_alpha          <= apply_wstrb({16'h0, reg_alpha}, wr_data_q, wr_strb_q)[15:0];
                    8'h2C: reg_kill_threshold <= apply_wstrb({16'h0, reg_kill_threshold}, wr_data_q, wr_strb_q)[15:0];
                    8'h30: clear_faults_pulse <= wr_data_q[0];
                    8'h34: begin
                        telem_start_pulse <= wr_data_q[0];
                        telem_clear_pulse <= wr_data_q[1];
                    end
                    8'h38: reg_telem_window   <= apply_wstrb(reg_telem_window, wr_data_q, wr_strb_q);
                    default: ;
                endcase

                bvalid     <= 1'b1;
                bresp      <= 1'b0; // OKAY response in this lightweight interface
                write_busy <= 1'b0;
            end else begin
                // Without BREADY in this scaffold interface, BVALID is a one-cycle pulse.
                bvalid <= 1'b0;
            end

            // Read accept.
            if (read_accept) begin
                arready   <= 1'b1;
                rd_addr_q <= araddr;
                read_busy <= 1'b1;
            end

            // Produce read data one cycle after address accept.
            if (read_busy) begin
                rdata     <= read_mux(rd_addr_q);
                rvalid    <= 1'b1;
                read_busy <= 1'b0;
            end else begin
                // Without RREADY in this scaffold interface, RVALID is a one-cycle pulse.
                rvalid <= 1'b0;
            end
        end
    end

    // ---------------------------------------------------------------------
    // Register outputs
    // ---------------------------------------------------------------------
    assign prbs_enable        = reg_prbs_enable;
    assign inv_delta_q        = reg_inv_delta_q;
    assign delta_adc_q        = reg_delta_adc_q;
    assign coeffs[0]          = reg_coeff0;
    assign coeffs[1]          = reg_coeff1;
    assign coeffs[2]          = reg_coeff2;
    assign coeffs[3]          = reg_coeff3;
    assign alpha              = reg_alpha;
    assign kill_threshold     = reg_kill_threshold;

    assign clear_faults       = clear_faults_pulse;
    assign telem_start_sample = telem_start_pulse;
    assign telem_clear_total  = telem_clear_pulse;
    assign telem_window_cycles= reg_telem_window;

endmodule
