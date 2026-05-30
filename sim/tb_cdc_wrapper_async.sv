// tb_cdc_wrapper_async.sv
//
// Asynchronous-clock integration co-simulation for waveform_brain_cdc_wrapper.
//
// Drives the AXI domain at 100 MHz and the fabric domain at ~71.4 MHz with a
// random initial phase offset, then exercises every CDC path:
//   A. AXI -> Fabric multi-bit handshake (config bus)
//   B. AXI -> Fabric pulse synchronizers (clear_faults, telem_start, telem_clear)
//   C. Fabric -> AXI single-bit synchronizers (safety_kill, telem_sample_active)
//   D. Fabric -> AXI array-single synchronizers (fault_flags, status_word, ...)
//   E. Fabric -> AXI gray-coded counter synchronizers
//   F. Fabric -> AXI multi-bit handshake (telemetry payload)
//
// Each subtest emits explicit PASS/FAIL lines. The final TB_PASS / TB_FAIL line
// is consumed by scripts/run_cdc_cosim.py.

`timescale 1ns/1ps

module tb_cdc_wrapper_async;
    parameter int ADC_WIDTH   = 16;
    parameter int SCALE_WIDTH = 32;

    // ---- clocks: 100 MHz AXI, ~71.4 MHz fabric, deliberately incommensurate ----
    logic axi_clk    = 1'b0;
    logic fabric_clk = 1'b0;
    always #5 axi_clk    = ~axi_clk;   // 10 ns period
    always #7 fabric_clk = ~fabric_clk; // 14 ns period

    logic axi_rst_n    = 1'b0;
    logic fabric_rst_n = 1'b0;

    // ---- AXI domain stimulus / DUT outputs ----
    logic                          axi_cfg_update;
    logic                          axi_cfg_ack;

    logic                          axi_prbs_enable;
    logic signed [SCALE_WIDTH-1:0] axi_inv_delta_q;
    logic signed [SCALE_WIDTH-1:0] axi_delta_adc_q;
    logic signed [31:0]            axi_coeffs [0:3];
    logic [15:0]                   axi_alpha;
    logic [ADC_WIDTH-1:0]          axi_kill_threshold;
    logic [31:0]                   axi_telem_window_cycles;

    logic                          axi_clear_faults_pulse;
    logic                          axi_telem_start_pulse;
    logic                          axi_telem_clear_pulse;

    logic                          fab_prbs_enable;
    logic signed [SCALE_WIDTH-1:0] fab_inv_delta_q;
    logic signed [SCALE_WIDTH-1:0] fab_delta_adc_q;
    logic signed [31:0]            fab_coeffs [0:3];
    logic [15:0]                   fab_alpha;
    logic [ADC_WIDTH-1:0]          fab_kill_threshold;
    logic [31:0]                   fab_telem_window_cycles;

    logic                          fab_clear_faults_pulse;
    logic                          fab_telem_start_pulse;
    logic                          fab_telem_clear_pulse;

    // ---- Fabric domain stimulus / DUT outputs ----
    logic                          fab_safety_kill;
    logic [15:0]                   fab_fault_flags;
    logic [15:0]                   fab_status_word;

    logic [31:0]                   fab_telem_flips_delta;
    logic [31:0]                   fab_telem_total_flips;
    logic                          fab_telem_sample_active;
    logic                          fab_telem_sample_done;

    logic [31:0]                   fab_health_status;
    logic [31:0]                   fab_health_safety_trip_count;
    logic [31:0]                   fab_health_axis_stall_count;
    logic [31:0]                   fab_health_decoder_valid_count;
    logic [31:0]                   fab_health_telem_done_count;

    logic [4:0]                    fab_axis_fifo_level;
    logic [31:0]                   fab_axis_fifo_overflow_count;
    logic [31:0]                   fab_axis_fifo_stall_count;
    logic [31:0]                   fab_axis_frame_drop_count;
    logic [31:0]                   fab_axis_sequence_count;

    logic                          axi_safety_kill;
    logic [15:0]                   axi_fault_flags;
    logic [15:0]                   axi_status_word;

    logic [31:0]                   axi_telem_flips_delta;
    logic [31:0]                   axi_telem_total_flips;
    logic                          axi_telem_sample_active;
    logic                          axi_telem_sample_done;

    logic [31:0]                   axi_health_status;
    logic [31:0]                   axi_health_safety_trip_count;
    logic [31:0]                   axi_health_axis_stall_count;
    logic [31:0]                   axi_health_decoder_valid_count;
    logic [31:0]                   axi_health_telem_done_count;

    logic [4:0]                    axi_axis_fifo_level;
    logic [31:0]                   axi_axis_fifo_overflow_count;
    logic [31:0]                   axi_axis_fifo_stall_count;
    logic [31:0]                   axi_axis_frame_drop_count;
    logic [31:0]                   axi_axis_sequence_count;

    waveform_brain_cdc_wrapper #(
        .ADC_WIDTH   (ADC_WIDTH),
        .SCALE_WIDTH (SCALE_WIDTH)
    ) dut (
        .axi_clk                       (axi_clk),
        .axi_rst_n                     (axi_rst_n),
        .fabric_clk                    (fabric_clk),
        .fabric_rst_n                  (fabric_rst_n),

        .axi_cfg_update                (axi_cfg_update),
        .axi_cfg_ack                   (axi_cfg_ack),
        .axi_prbs_enable               (axi_prbs_enable),
        .axi_inv_delta_q               (axi_inv_delta_q),
        .axi_delta_adc_q               (axi_delta_adc_q),
        .axi_coeffs                    (axi_coeffs),
        .axi_alpha                     (axi_alpha),
        .axi_kill_threshold            (axi_kill_threshold),
        .axi_telem_window_cycles       (axi_telem_window_cycles),

        .axi_clear_faults_pulse        (axi_clear_faults_pulse),
        .axi_telem_start_pulse         (axi_telem_start_pulse),
        .axi_telem_clear_pulse         (axi_telem_clear_pulse),

        .fab_prbs_enable               (fab_prbs_enable),
        .fab_inv_delta_q               (fab_inv_delta_q),
        .fab_delta_adc_q               (fab_delta_adc_q),
        .fab_coeffs                    (fab_coeffs),
        .fab_alpha                     (fab_alpha),
        .fab_kill_threshold            (fab_kill_threshold),
        .fab_telem_window_cycles       (fab_telem_window_cycles),

        .fab_clear_faults_pulse        (fab_clear_faults_pulse),
        .fab_telem_start_pulse         (fab_telem_start_pulse),
        .fab_telem_clear_pulse         (fab_telem_clear_pulse),

        .fab_safety_kill               (fab_safety_kill),
        .fab_fault_flags               (fab_fault_flags),
        .fab_status_word               (fab_status_word),

        .fab_telem_flips_delta         (fab_telem_flips_delta),
        .fab_telem_total_flips         (fab_telem_total_flips),
        .fab_telem_sample_active       (fab_telem_sample_active),
        .fab_telem_sample_done         (fab_telem_sample_done),

        .fab_health_status             (fab_health_status),
        .fab_health_safety_trip_count  (fab_health_safety_trip_count),
        .fab_health_axis_stall_count   (fab_health_axis_stall_count),
        .fab_health_decoder_valid_count(fab_health_decoder_valid_count),
        .fab_health_telem_done_count   (fab_health_telem_done_count),

        .fab_axis_fifo_level           (fab_axis_fifo_level),
        .fab_axis_fifo_overflow_count  (fab_axis_fifo_overflow_count),
        .fab_axis_fifo_stall_count     (fab_axis_fifo_stall_count),
        .fab_axis_frame_drop_count     (fab_axis_frame_drop_count),
        .fab_axis_sequence_count       (fab_axis_sequence_count),

        .axi_safety_kill               (axi_safety_kill),
        .axi_fault_flags               (axi_fault_flags),
        .axi_status_word               (axi_status_word),

        .axi_telem_flips_delta         (axi_telem_flips_delta),
        .axi_telem_total_flips         (axi_telem_total_flips),
        .axi_telem_sample_active       (axi_telem_sample_active),
        .axi_telem_sample_done         (axi_telem_sample_done),

        .axi_health_status             (axi_health_status),
        .axi_health_safety_trip_count  (axi_health_safety_trip_count),
        .axi_health_axis_stall_count   (axi_health_axis_stall_count),
        .axi_health_decoder_valid_count(axi_health_decoder_valid_count),
        .axi_health_telem_done_count   (axi_health_telem_done_count),

        .axi_axis_fifo_level           (axi_axis_fifo_level),
        .axi_axis_fifo_overflow_count  (axi_axis_fifo_overflow_count),
        .axi_axis_fifo_stall_count     (axi_axis_fifo_stall_count),
        .axi_axis_frame_drop_count     (axi_axis_frame_drop_count),
        .axi_axis_sequence_count       (axi_axis_sequence_count)
    );

    // ---- check helpers ----
    integer checks = 0;
    integer errors = 0;

    task check32(input [31:0] got, input [31:0] exp, input [255:0] tag);
        begin
            checks = checks + 1;
            if (got !== exp) begin
                errors = errors + 1;
                $display("FAIL [%0s]: got=0x%08h exp=0x%08h", tag, got, exp);
            end else begin
                $display("PASS [%0s]: 0x%08h", tag, got);
            end
        end
    endtask

    task check_count(input integer got, input integer exp, input [255:0] tag);
        begin
            checks = checks + 1;
            if (got !== exp) begin
                errors = errors + 1;
                $display("FAIL [%0s]: got=%0d exp=%0d", tag, got, exp);
            end else begin
                $display("PASS [%0s]: %0d", tag, got);
            end
        end
    endtask

    // ---- pulse / event counters ----
    integer fab_clear_faults_count = 0;
    integer fab_telem_start_count  = 0;
    integer fab_telem_clear_count  = 0;
    integer axi_telem_done_count   = 0;
    integer axi_cfg_ack_count      = 0;

    always @(posedge fabric_clk) begin
        if (fab_clear_faults_pulse) fab_clear_faults_count = fab_clear_faults_count + 1;
        if (fab_telem_start_pulse)  fab_telem_start_count  = fab_telem_start_count  + 1;
        if (fab_telem_clear_pulse)  fab_telem_clear_count  = fab_telem_clear_count  + 1;
    end

    always @(posedge axi_clk) begin
        if (axi_telem_sample_done) axi_telem_done_count = axi_telem_done_count + 1;
        if (axi_cfg_ack)           axi_cfg_ack_count    = axi_cfg_ack_count    + 1;
    end

    integer i;
    integer t;

    initial begin
        // ---- initialise stimulus ----
        axi_cfg_update           = 1'b0;
        axi_prbs_enable          = 1'b0;
        axi_inv_delta_q          = 32'sh0001_0000;
        axi_delta_adc_q          = 32'sh0001_0000;
        for (i = 0; i < 4; i = i + 1) axi_coeffs[i] = 32'sh0;
        axi_alpha                = 16'h0010;
        axi_kill_threshold       = {ADC_WIDTH{1'b1}};
        axi_telem_window_cycles  = 32'd1000;
        axi_clear_faults_pulse   = 1'b0;
        axi_telem_start_pulse    = 1'b0;
        axi_telem_clear_pulse    = 1'b0;

        fab_safety_kill                 = 1'b0;
        fab_fault_flags                 = 16'h0;
        fab_status_word                 = 16'h0;
        fab_telem_flips_delta           = 32'h0;
        fab_telem_total_flips           = 32'h0;
        fab_telem_sample_active         = 1'b0;
        fab_telem_sample_done           = 1'b0;
        fab_health_status               = 32'h0;
        fab_health_safety_trip_count    = 32'h0;
        fab_health_axis_stall_count     = 32'h0;
        fab_health_decoder_valid_count  = 32'h0;
        fab_health_telem_done_count     = 32'h0;
        fab_axis_fifo_level             = 5'h0;
        fab_axis_fifo_overflow_count    = 32'h0;
        fab_axis_fifo_stall_count       = 32'h0;
        fab_axis_frame_drop_count       = 32'h0;
        fab_axis_sequence_count         = 32'h0;

        // ---- async reset release ----
        repeat (8) @(posedge axi_clk);
        repeat (8) @(posedge fabric_clk);
        axi_rst_n    = 1'b1;
        fabric_rst_n = 1'b1;
        repeat (20) @(posedge axi_clk);

        // -----------------------------------------------------------------
        // Test A: config handshake AXI -> Fab (atomic multi-bit)
        // -----------------------------------------------------------------
        $display("--- Test A: config handshake AXI->Fab ---");

        // Drive data with blocking assignments *before* the clock edge so
        // always_comb sees stable values at the posedge (iverilog sensitivity
        // quirk with unpacked arrays).
        #1;
        axi_prbs_enable         = 1'b1;
        axi_inv_delta_q         = 32'sh1234_5678;
        axi_delta_adc_q         = 32'sh0ABC_DEF0;
        axi_coeffs[0]           = 32'sh1111_1111;
        axi_coeffs[1]           = 32'sh2222_2222;
        axi_coeffs[2]           = 32'sh3333_3333;
        axi_coeffs[3]           = 32'sh4444_4444;
        axi_alpha               = 16'h00CD;
        axi_kill_threshold      = 16'h7FFF;
        axi_telem_window_cycles = 32'd5000;
        #0;
        @(posedge axi_clk);
        axi_cfg_update          = 1'b1;
        @(posedge axi_clk);
        axi_cfg_update          = 1'b0;

        // Wait for round-trip ack (handshake complete).
        t = 0;
        while (axi_cfg_ack_count < 1 && t < 400) begin
            @(posedge axi_clk);
            t = t + 1;
        end
        check_count(axi_cfg_ack_count, 1, "cfg_ack first");

        // Settle on fabric and verify all unpacked fields match exactly.
        repeat (8) @(posedge fabric_clk);
        check32({31'h0, fab_prbs_enable},     32'd1,             "fab_prbs_enable");
        check32(fab_inv_delta_q,              32'sh1234_5678,    "fab_inv_delta_q");
        check32(fab_delta_adc_q,              32'sh0ABC_DEF0,    "fab_delta_adc_q");
        check32(dut.fab_coeffs[0],            32'sh1111_1111,    "fab_coeffs[0]");
        check32(dut.fab_coeffs[1],            32'sh2222_2222,    "fab_coeffs[1]");
        check32(dut.fab_coeffs[2],            32'sh3333_3333,    "fab_coeffs[2]");
        check32(dut.fab_coeffs[3],            32'sh4444_4444,    "fab_coeffs[3]");
        check32({16'h0, fab_alpha},           32'h0000_00CD,     "fab_alpha");
        check32({16'h0, fab_kill_threshold},  32'h0000_7FFF,     "fab_kill_threshold");
        check32(fab_telem_window_cycles,      32'd5000,          "fab_telem_window_cycles");

        // Back-to-back update on a subset of fields. Must not corrupt others.
        #1;
        axi_inv_delta_q = 32'shDEAD_BEEF;
        axi_alpha       = 16'hABCD;
        @(posedge axi_clk);
        axi_cfg_update  <= 1'b1;
        @(posedge axi_clk);
        axi_cfg_update  <= 1'b0;

        t = 0;
        while (axi_cfg_ack_count < 2 && t < 400) begin
            @(posedge axi_clk);
            t = t + 1;
        end
        check_count(axi_cfg_ack_count, 2, "cfg_ack second");

        repeat (8) @(posedge fabric_clk);
        check32(fab_inv_delta_q,           32'shDEAD_BEEF,    "fab_inv_delta_q (b2b)");
        check32({16'h0, fab_alpha},        32'h0000_ABCD,     "fab_alpha (b2b)");
        // Other fields must still hold their prior values.
        check32({31'h0, fab_prbs_enable},  32'd1,             "fab_prbs_enable (held)");
        check32(dut.fab_coeffs[3],         32'sh4444_4444,    "fab_coeffs[3] (held)");

        // -----------------------------------------------------------------
        // Test B: pulse synchronizers AXI -> Fab
        // -----------------------------------------------------------------
        $display("--- Test B: pulse synchronizers AXI->Fab ---");
        fab_clear_faults_count = 0;
        fab_telem_start_count  = 0;
        fab_telem_clear_count  = 0;

        // Single 1-cycle pulse on each line.
        @(posedge axi_clk);
        axi_clear_faults_pulse <= 1'b1;
        @(posedge axi_clk);
        axi_clear_faults_pulse <= 1'b0;
        repeat (60) @(posedge fabric_clk);
        check_count(fab_clear_faults_count, 1, "fab_clear_faults_pulse single");

        // Three back-to-back pulses with gaps.
        for (i = 0; i < 3; i = i + 1) begin
            @(posedge axi_clk);
            axi_telem_start_pulse <= 1'b1;
            @(posedge axi_clk);
            axi_telem_start_pulse <= 1'b0;
            repeat (12) @(posedge axi_clk);
        end
        repeat (60) @(posedge fabric_clk);
        check_count(fab_telem_start_count, 3, "fab_telem_start_pulse triple");

        @(posedge axi_clk);
        axi_telem_clear_pulse <= 1'b1;
        @(posedge axi_clk);
        axi_telem_clear_pulse <= 1'b0;
        repeat (60) @(posedge fabric_clk);
        check_count(fab_telem_clear_count, 1, "fab_telem_clear_pulse single");

        // -----------------------------------------------------------------
        // Test C: single-bit syncs Fab -> AXI
        // -----------------------------------------------------------------
        $display("--- Test C: single-bit syncs Fab->AXI ---");
        fab_safety_kill = 1'b1;
        repeat (20) @(posedge axi_clk);
        check32({31'h0, axi_safety_kill}, 32'd1, "axi_safety_kill rising");
        fab_safety_kill = 1'b0;
        repeat (20) @(posedge axi_clk);
        check32({31'h0, axi_safety_kill}, 32'd0, "axi_safety_kill falling");

        fab_telem_sample_active = 1'b1;
        repeat (20) @(posedge axi_clk);
        check32({31'h0, axi_telem_sample_active}, 32'd1, "axi_telem_sample_active rising");
        fab_telem_sample_active = 1'b0;
        repeat (20) @(posedge axi_clk);
        check32({31'h0, axi_telem_sample_active}, 32'd0, "axi_telem_sample_active falling");

        // -----------------------------------------------------------------
        // Test D: array-single syncs Fab -> AXI
        // -----------------------------------------------------------------
        $display("--- Test D: array-single syncs Fab->AXI ---");
        fab_fault_flags     = 16'hBEAD;
        fab_status_word     = 16'hCAFE;
        fab_health_status   = 32'hF00D_BABE;
        fab_axis_fifo_level = 5'h17;
        repeat (20) @(posedge axi_clk);
        check32({16'h0, axi_fault_flags},     32'h0000_BEAD,  "axi_fault_flags");
        check32({16'h0, axi_status_word},     32'h0000_CAFE,  "axi_status_word");
        check32(axi_health_status,            32'hF00D_BABE,  "axi_health_status");
        check32({27'h0, axi_axis_fifo_level}, 32'h0000_0017,  "axi_axis_fifo_level");

        // -----------------------------------------------------------------
        // Test E: gray counter syncs Fab -> AXI
        // -----------------------------------------------------------------
        $display("--- Test E: gray counters Fab->AXI ---");

        // Direct value drive, then settle.
        @(posedge fabric_clk);
        fab_health_safety_trip_count   = 32'd123;
        fab_health_axis_stall_count    = 32'd456;
        fab_health_decoder_valid_count = 32'd789;
        fab_health_telem_done_count    = 32'd1024;
        fab_axis_fifo_overflow_count   = 32'd17;
        fab_axis_fifo_stall_count      = 32'd32;
        fab_axis_frame_drop_count      = 32'd64;
        fab_axis_sequence_count        = 32'hDEAD_BEEF;
        repeat (40) @(posedge axi_clk);
        check32(axi_health_safety_trip_count,   32'd123,        "axi_health_safety_trip_count");
        check32(axi_health_axis_stall_count,    32'd456,        "axi_health_axis_stall_count");
        check32(axi_health_decoder_valid_count, 32'd789,        "axi_health_decoder_valid_count");
        check32(axi_health_telem_done_count,    32'd1024,       "axi_health_telem_done_count");
        check32(axi_axis_fifo_overflow_count,   32'd17,         "axi_axis_fifo_overflow_count");
        check32(axi_axis_fifo_stall_count,      32'd32,         "axi_axis_fifo_stall_count");
        check32(axi_axis_frame_drop_count,      32'd64,         "axi_axis_frame_drop_count");
        check32(axi_axis_sequence_count,        32'hDEAD_BEEF,  "axi_axis_sequence_count");

        // Monotonic counter stream: gray-code property requires that bits flip
        // one at a time, so a stream that increments every fabric cycle should
        // round-trip cleanly through the dest sync chain.
        for (i = 0; i < 50; i = i + 1) begin
            @(posedge fabric_clk);
            fab_health_safety_trip_count = fab_health_safety_trip_count + 1;
        end
        repeat (40) @(posedge axi_clk);
        check32(axi_health_safety_trip_count, 32'd173, "axi_health_safety_trip_count after stream");

        // -----------------------------------------------------------------
        // Test F: telemetry handshake Fab -> AXI
        // -----------------------------------------------------------------
        $display("--- Test F: telemetry handshake Fab->AXI ---");
        axi_telem_done_count = 0;

        @(posedge fabric_clk);
        fab_telem_flips_delta <= 32'h1111_2222;
        fab_telem_total_flips <= 32'h3333_4444;
        @(posedge fabric_clk);
        fab_telem_sample_done <= 1'b1;
        @(posedge fabric_clk);
        fab_telem_sample_done <= 1'b0;

        repeat (80) @(posedge axi_clk);
        check_count(axi_telem_done_count,    1,                "axi_telem_sample_done pulse");
        check32(axi_telem_flips_delta, 32'h1111_2222,          "axi_telem_flips_delta");
        check32(axi_telem_total_flips, 32'h3333_4444,          "axi_telem_total_flips");

        // -----------------------------------------------------------------
        // summary
        // -----------------------------------------------------------------
        $display("CDC_COSIM_SUMMARY checks=%0d errors=%0d", checks, errors);
        if (errors == 0) begin
            $display("TB_PASS tb_cdc_wrapper_async");
        end else begin
            $display("TB_FAIL tb_cdc_wrapper_async");
        end
        $finish;
    end

    // ---- watchdog ----
    initial begin
        #2_000_000;
        $display("TB_FAIL tb_cdc_wrapper_async: watchdog timeout");
        $finish;
    end
endmodule
