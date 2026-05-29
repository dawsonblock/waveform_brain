`timescale 1ns/1ps

module tb_telemetry_counter_window;
    logic clk;
    logic rst_n;
    logic [3:0] valid_in;
    logic [1:0] syndrome [0:3];
    logic start_sample;
    logic clear_total;
    logic [31:0] window_cycles;
    logic sample_active;
    logic sample_done;
    logic [31:0] flips_delta;
    logic [31:0] total_flips;

    telemetry_counter dut (
        .clk          (clk),
        .rst_n        (rst_n),
        .valid_in     (valid_in),
        .syndrome     (syndrome),
        .start_sample (start_sample),
        .clear_total  (clear_total),
        .window_cycles(window_cycles),
        .sample_active(sample_active),
        .sample_done  (sample_done),
        .flips_delta  (flips_delta),
        .total_flips  (total_flips)
    );

    initial clk = 1'b0;
    always #5 clk = ~clk;

    task automatic run_one_cycle_window(
        input logic [1:0] syndrome_ch0,
        input logic [31:0] exp_delta,
        input logic [31:0] exp_total
    );
        integer wait_cycles;
    begin
        start_sample = 1'b1;
        valid_in = 4'b0000;
        @(posedge clk);

        start_sample = 1'b0;
        valid_in = 4'b0001;
        syndrome[0] = syndrome_ch0;
        for (wait_cycles = 0; wait_cycles < 3; wait_cycles = wait_cycles + 1) begin
            @(posedge clk);
            #1;
        end

        if (flips_delta !== exp_delta) begin
            $fatal(
                1,
                "flips_delta mismatch: got %0d expected %0d",
                flips_delta,
                exp_delta
            );
        end
        if (total_flips !== exp_total) begin
            $fatal(
                1,
                "total_flips mismatch: got %0d expected %0d",
                total_flips,
                exp_total
            );
        end

        valid_in = 4'b0000;
    end
    endtask

    integer idx;
    initial begin
        rst_n = 1'b0;
        valid_in = 4'b0000;
        start_sample = 1'b0;
        clear_total = 1'b0;
        window_cycles = 32'd1;
        for (idx = 0; idx < 4; idx = idx + 1) begin
            syndrome[idx] = 2'b00;
        end

        repeat (3) @(posedge clk);
        rst_n = 1'b1;
        @(posedge clk);

        // First one-cycle window: one change on channel 0 should be counted.
        run_one_cycle_window(2'b01, 32'd1, 32'd1);

        $display("TB_PASS tb_telemetry_counter_window");
        $finish;
    end
endmodule
