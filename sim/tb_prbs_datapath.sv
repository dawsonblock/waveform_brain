`timescale 1ns/1ps

module tb_prbs_datapath;
    localparam int ADC_WIDTH = 16;
    localparam int SCALE_WIDTH = 32;

    logic clk;
    logic rst_n;
    logic signed [ADC_WIDTH-1:0] adc_in [0:3];
    logic prbs_enable;
    logic signed [SCALE_WIDTH-1:0] inv_delta_q;
    logic signed [SCALE_WIDTH-1:0] delta_adc_q;
    logic signed [31:0] coeffs [0:3];
    logic [15:0] alpha;
    logic [ADC_WIDTH-1:0] kill_threshold;
    logic clear_faults;
    logic telem_start_sample;
    logic telem_clear_total;
    logic [31:0] telem_window_cycles;
    logic [63:0] m_axis_tdata;
    logic m_axis_tvalid;
    logic m_axis_tready;
    logic m_axis_tlast;
    logic safety_kill;
    logic [15:0] fault_flags;
    logic [15:0] status_word;
    logic [31:0] telem_flips_delta;
    logic [31:0] telem_total_flips;
    logic telem_sample_active;
    logic telem_sample_done;
    logic [31:0] health_status;
    logic [31:0] health_safety_trip_count;
    logic [31:0] health_axis_stall_count;
    logic [31:0] health_decoder_valid_count;
    logic [31:0] health_telem_done_count;
    logic [4:0] axis_fifo_level;
    logic [31:0] axis_fifo_overflow_count;
    logic [31:0] axis_fifo_stall_count;
    logic [31:0] axis_frame_drop_count;
    logic [31:0] axis_sequence_count;

    int errors;
    int prbs_seen;
    logic signed [ADC_WIDTH-1:0] prev_prbs_sample;

    waveform_control_4q_top #(
        .ADC_WIDTH(ADC_WIDTH),
        .SCALE_WIDTH(SCALE_WIDTH)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .adc_in(adc_in),
        .prbs_enable(prbs_enable),
        .inv_delta_q(inv_delta_q),
        .delta_adc_q(delta_adc_q),
        .coeffs(coeffs),
        .alpha(alpha),
        .kill_threshold(kill_threshold),
        .clear_faults(clear_faults),
        .telem_start_sample(telem_start_sample),
        .telem_clear_total(telem_clear_total),
        .telem_window_cycles(telem_window_cycles),
        .m_axis_tdata(m_axis_tdata),
        .m_axis_tvalid(m_axis_tvalid),
        .m_axis_tready(m_axis_tready),
        .m_axis_tlast(m_axis_tlast),
        .safety_kill(safety_kill),
        .fault_flags(fault_flags),
        .status_word(status_word),
        .telem_flips_delta(telem_flips_delta),
        .telem_total_flips(telem_total_flips),
        .telem_sample_active(telem_sample_active),
        .telem_sample_done(telem_sample_done),
        .health_status(health_status),
        .health_safety_trip_count(health_safety_trip_count),
        .health_axis_stall_count(health_axis_stall_count),
        .health_decoder_valid_count(health_decoder_valid_count),
        .health_telem_done_count(health_telem_done_count),
        .axis_fifo_level(axis_fifo_level),
        .axis_fifo_overflow_count(axis_fifo_overflow_count),
        .axis_fifo_stall_count(axis_fifo_stall_count),
        .axis_frame_drop_count(axis_frame_drop_count),
        .axis_sequence_count(axis_sequence_count)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    task automatic expect_effective_matches_adc(string label);
        begin
            @(posedge clk);
            #1;
            for (int ch = 0; ch < 4; ch++) begin
                if (dut.effective_adc[ch] !== adc_in[ch]) begin
                    errors = errors + 1;
                    $display(
                        "TB_ERROR %s ch=%0d expected_adc=%0d got=%0d",
                        label,
                        ch,
                        adc_in[ch],
                        dut.effective_adc[ch]
                    );
                end
            end
        end
    endtask

    task automatic expect_effective_matches_prbs(string label);
        begin
            @(posedge clk);
            #1;
            for (int ch = 0; ch < 4; ch++) begin
                if (dut.effective_adc[ch] !== dut.prbs_sample) begin
                    errors = errors + 1;
                    $display(
                        "TB_ERROR %s ch=%0d expected_prbs=%0d got=%0d",
                        label,
                        ch,
                        dut.prbs_sample,
                        dut.effective_adc[ch]
                    );
                end
            end
        end
    endtask

    always @(posedge clk) begin
        if (rst_n && prbs_enable) begin
            if (dut.prbs_sample !== prev_prbs_sample) begin
                prbs_seen <= prbs_seen + 1;
            end
            prev_prbs_sample <= dut.prbs_sample;
        end
    end

    initial begin
        errors = 0;
        prbs_seen = 0;
        prev_prbs_sample = '0;
        rst_n = 1'b0;
        prbs_enable = 1'b0;
        inv_delta_q = 32'sh0001_0000;
        delta_adc_q = 32'sh0001_0000;
        coeffs[0] = 32'sh0;
        coeffs[1] = 32'sh0;
        coeffs[2] = 32'sh0;
        coeffs[3] = 32'sh0;
        alpha = 16'h0010;
        kill_threshold = 16'h7fff;
        clear_faults = 1'b0;
        telem_start_sample = 1'b0;
        telem_clear_total = 1'b0;
        telem_window_cycles = 32'd16;
        m_axis_tready = 1'b1;

        adc_in[0] = 16'sd11;
        adc_in[1] = -16'sd22;
        adc_in[2] = 16'sd33;
        adc_in[3] = -16'sd44;

        repeat (2) @(posedge clk);
        rst_n = 1'b1;

        expect_effective_matches_adc("prbs_disabled_paths");

        prbs_enable = 1'b1;
        repeat (6) begin
            expect_effective_matches_prbs("prbs_enabled_paths");
        end

        prbs_enable = 1'b0;
        expect_effective_matches_adc("prbs_re_disabled_paths");

        if (prbs_seen == 0) begin
            errors = errors + 1;
            $display("TB_ERROR prbs_sequence_not_observable");
        end

        if (errors == 0) begin
            $display("TB_PASS tb_prbs_datapath");
            $finish(0);
        end else begin
            $display("TB_FAIL tb_prbs_datapath errors=%0d", errors);
            $finish(1);
        end
    end
endmodule
