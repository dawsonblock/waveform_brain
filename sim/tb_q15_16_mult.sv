`timescale 1ns/1ps

module tb_q15_16_mult;
    logic clk;
    logic rst_n;
    logic valid_in;
    logic signed [31:0] a;
    logic signed [31:0] b;
    logic valid_out;
    logic signed [31:0] result;
    logic overflow;

    q15_16_mult dut (
        .clk      (clk),
        .rst_n    (rst_n),
        .valid_in (valid_in),
        .a        (a),
        .b        (b),
        .valid_out(valid_out),
        .result   (result),
        .overflow (overflow)
    );

    initial clk = 1'b0;
    always #5 clk = ~clk;

    task automatic apply_and_check(
        input logic signed [31:0] ta,
        input logic signed [31:0] tb,
        input logic signed [31:0] exp_result,
        input logic exp_overflow
    );
    begin
        a = ta;
        b = tb;
        valid_in = 1'b1;
        @(posedge clk);
        #1;
        if (valid_out !== 1'b1) begin
            $fatal(1, "valid_out was not asserted for input a=%0d b=%0d", ta, tb);
        end
        if (result !== exp_result) begin
            $fatal(
                1,
                "result mismatch: got %0d (0x%08h) expected %0d (0x%08h)",
                result,
                result,
                exp_result,
                exp_result
            );
        end
        if (overflow !== exp_overflow) begin
            $fatal(
                1,
                "overflow mismatch: got %0b expected %0b",
                overflow,
                exp_overflow
            );
        end
    end
    endtask

    task automatic apply_and_check_overflow(
        input logic signed [31:0] ta,
        input logic signed [31:0] tb
    );
    begin
        a = ta;
        b = tb;
        valid_in = 1'b1;
        @(posedge clk);
        #1;
        if (valid_out !== 1'b1) begin
            $fatal(1, "valid_out not asserted for overflow vector");
        end
        if (overflow !== 1'b1) begin
            $fatal(1, "overflow expected high for overflow vector");
        end
    end
    endtask

    initial begin
        rst_n = 1'b0;
        valid_in = 1'b0;
        a = '0;
        b = '0;

        repeat (3) @(posedge clk);
        rst_n = 1'b1;
        @(posedge clk);

        // 1.0 * 2.0 = 2.0 (Q15.16: 0x00020000)
        apply_and_check(32'sh0001_0000, 32'sh0002_0000, 32'sh0002_0000, 1'b0);

        // 0.5 * 0.5 = 0.25 (Q15.16: 0x00004000)
        apply_and_check(32'sh0000_8000, 32'sh0000_8000, 32'sh0000_4000, 1'b0);

        // Large operands should set overflow.
        apply_and_check_overflow(32'sh7FFF_FFFF, 32'sh7FFF_FFFF);

        valid_in = 1'b0;
        @(posedge clk);

        $display("TB_PASS tb_q15_16_mult");
        $finish;
    end
endmodule
