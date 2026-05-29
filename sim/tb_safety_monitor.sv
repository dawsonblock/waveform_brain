`timescale 1ns/1ps

module tb_safety_monitor;
    localparam int ADC_WIDTH = 16;
    localparam int CH = 4;

    logic                         clk;
    logic                         rst_n;
    logic signed [ADC_WIDTH-1:0]  adc_in [0:CH-1];
    logic [ADC_WIDTH-1:0]         kill_threshold;
    logic                         clear_faults;
    logic [CH-1:0]                safety_kill;
    logic [CH-1:0]                fault_latched;

    int errors;

    generate
        for (genvar ch = 0; ch < CH; ch++) begin : g_dut
            safety_monitor #(
                .ADC_WIDTH(ADC_WIDTH)
            ) dut (
                .clk(clk),
                .rst_n(rst_n),
                .adc_in(adc_in[ch]),
                .kill_threshold(kill_threshold),
                .clear_faults(clear_faults),
                .safety_kill(safety_kill[ch]),
                .fault_latched(fault_latched[ch])
            );
        end
    endgenerate

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    task automatic drive_one_and_expect(
        input int channel,
        input logic signed [ADC_WIDTH-1:0] sample,
        input logic [CH-1:0] expected_latched,
        input string label
    );
        begin
            adc_in[channel] = sample;
            @(posedge clk);
            #1;
            if (fault_latched !== expected_latched) begin
                errors = errors + 1;
                $display(
                    "TB_ERROR %s ch=%0d sample=%0d expected=%0b got=%0b",
                    label,
                    channel,
                    sample,
                    expected_latched,
                    fault_latched
                );
            end
        end
    endtask

    initial begin
        errors = 0;
        rst_n = 1'b0;
        for (int ch = 0; ch < CH; ch++) begin
            adc_in[ch] = '0;
        end
        clear_faults = 1'b0;
        kill_threshold = 16'd100;

        repeat (2) @(posedge clk);
        rst_n = 1'b1;

        drive_one_and_expect(0, 16'sd0, 4'b0000, "ch0_zero");
        drive_one_and_expect(1, 16'sd0, 4'b0000, "ch1_zero");
        drive_one_and_expect(2, 16'sd0, 4'b0000, "ch2_zero");
        drive_one_and_expect(3, 16'sd0, 4'b0000, "ch3_zero");

        drive_one_and_expect(0, 16'sd101, 4'b0001, "ch0_trip_plus");
        drive_one_and_expect(1, 16'sd101, 4'b0011, "ch1_trip_plus");
        drive_one_and_expect(2, -16'sd101, 4'b0111, "ch2_trip_minus");
        drive_one_and_expect(3, -16'sh8000, 4'b1111, "ch3_trip_most_negative");

        for (int ch = 0; ch < CH; ch++) begin
            adc_in[ch] = 16'sd0;
        end
        @(posedge clk);
        #1;
        if (fault_latched !== 4'b1111) begin
            errors = errors + 1;
            $display("TB_ERROR sticky_faults_not_held got=%0b", fault_latched);
        end

        clear_faults = 1'b1;
        @(posedge clk);
        #1;
        clear_faults = 1'b0;
        if (fault_latched !== 4'b0000) begin
            errors = errors + 1;
            $display("TB_ERROR clear_faults_did_not_clear");
        end

        drive_one_and_expect(2, 16'sd100, 4'b0000, "ch2_at_threshold_no_trip");
        drive_one_and_expect(2, -16'sd100, 4'b0000, "ch2_neg_threshold_no_trip");
        drive_one_and_expect(2, -16'sd101, 4'b0100, "ch2_neg_threshold_trip");

        clear_faults = 1'b1;
        @(posedge clk);
        #1;
        clear_faults = 1'b0;
        if (fault_latched !== 4'b0000) begin
            errors = errors + 1;
            $display("TB_ERROR final_clear_faults_did_not_clear");
        end

        for (int ch = 0; ch < CH; ch++) begin
            if (safety_kill[ch] !== fault_latched[ch]) begin
                errors = errors + 1;
                $display("TB_ERROR safety_kill_mismatch ch=%0d", ch);
            end
        end

        if (errors == 0) begin
            $display("TB_PASS tb_safety_monitor");
            $finish(0);
        end else begin
            $display("TB_FAIL tb_safety_monitor errors=%0d", errors);
            $finish(1);
        end
    end
endmodule
