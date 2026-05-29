`timescale 1ns/1ps

module tb_packer_axis_stall;
  logic clk = 1'b0;
  logic rst_n = 1'b0;
  logic clear = 1'b0;

  logic [3:0] valid_in;
  logic signed [15:0] data_in [0:3];
  logic [1:0] syndrome [0:3];
  logic fault_latched;

  logic [63:0] m_axis_tdata;
  logic        m_axis_tvalid;
  logic        m_axis_tready;
  logic        m_axis_tlast;

  logic [31:0] sequence_counter;
  logic [31:0] frame_drop_count;

  int errors = 0;
  logic [63:0] hold_data;
  logic hold_last;

  always #5 clk = ~clk;

  packer_axis dut (
      .clk(clk),
      .rst_n(rst_n),
      .clear(clear),
      .valid_in(valid_in),
      .data_in(data_in),
      .syndrome(syndrome),
      .fault_latched(fault_latched),
      .m_axis_tdata(m_axis_tdata),
      .m_axis_tvalid(m_axis_tvalid),
      .m_axis_tready(m_axis_tready),
      .m_axis_tlast(m_axis_tlast),
      .sequence_counter(sequence_counter),
      .frame_drop_count(frame_drop_count)
  );

  task automatic drive_frame(
      input [15:0] d0,
      input [15:0] d1,
      input [15:0] d2,
      input [15:0] d3
  );
    begin
      data_in[0] = d0;
      data_in[1] = d1;
      data_in[2] = d2;
      data_in[3] = d3;
      valid_in = 4'hF;
      @(posedge clk);
      valid_in = 4'h0;
    end
  endtask

  task automatic check_eq64(
      input [63:0] got,
      input [63:0] exp,
      input [255:0] msg
  );
    begin
      if (got !== exp) begin
        $display("FAIL %s got=%h exp=%h", msg, got, exp);
        errors = errors + 1;
      end
    end
  endtask

  initial begin
    logic [63:0] expected_beat0;
    logic [15:0] expected_meta;

    valid_in = 4'h0;
    data_in[0] = 16'h0;
    data_in[1] = 16'h0;
    data_in[2] = 16'h0;
    data_in[3] = 16'h0;
    syndrome[0] = 2'b01;
    syndrome[1] = 2'b10;
    syndrome[2] = 2'b11;
    syndrome[3] = 2'b00;
    fault_latched = 1'b1;
    m_axis_tready = 1'b0;

    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    @(posedge clk);

    expected_beat0 = {16'h4444, 16'h3333, 16'h2222, 16'h1111};
    expected_meta = {4'h2, 3'b000, 1'b1, 2'b00, 2'b11, 2'b10, 2'b01};

    drive_frame(16'h1111, 16'h2222, 16'h3333, 16'h4444);

    // Stall beat 0 and ensure hold stability.
    repeat (2) begin
      @(posedge clk);
      if (!m_axis_tvalid || m_axis_tlast) begin
        $display("FAIL beat0 expected valid, non-last during stall");
        errors = errors + 1;
      end
      check_eq64(m_axis_tdata, expected_beat0, "beat0 data while stalled");
    end

    hold_data = m_axis_tdata;
    hold_last = m_axis_tlast;
    @(posedge clk);
    if ((m_axis_tdata !== hold_data) || (m_axis_tlast !== hold_last)) begin
      $display("FAIL beat0 changed while stalled");
      errors = errors + 1;
    end

    // Accept beat 0.
    m_axis_tready = 1'b1;
    @(posedge clk);

    // Stall beat 1 and ensure hold stability.
    m_axis_tready = 1'b0;
    @(posedge clk);
    if (!m_axis_tvalid || !m_axis_tlast) begin
      $display("FAIL beat1 expected valid+last during stall");
      errors = errors + 1;
    end
    check_eq64(
        m_axis_tdata,
        {expected_meta, 16'h0000, 32'h0000_0000},
        "beat1 data"
    );

    hold_data = m_axis_tdata;
    hold_last = m_axis_tlast;

    // New incoming frame while busy should be dropped/count incremented.
    drive_frame(16'hAAAA, 16'hBBBB, 16'hCCCC, 16'hDDDD);
    @(posedge clk);
    if ((m_axis_tdata !== hold_data) || (m_axis_tlast !== hold_last)) begin
      $display("FAIL beat1 changed while stalled");
      errors = errors + 1;
    end

    if (frame_drop_count != 32'd1) begin
      $display("FAIL frame_drop_count got=%0d exp=1", frame_drop_count);
      errors = errors + 1;
    end

    if (sequence_counter != 32'd1) begin
      $display("FAIL sequence_counter got=%0d exp=1", sequence_counter);
      errors = errors + 1;
    end

    // Accept beat 1.
    m_axis_tready = 1'b1;
    @(posedge clk);

    // Return to idle.
    @(posedge clk);
    if (m_axis_tvalid) begin
      $display("FAIL expected idle after beat1 accept");
      errors = errors + 1;
    end

    if (errors == 0) begin
      $display("TB_PASS tb_packer_axis_stall");
      $finish;
    end

    $display("TB_FAIL tb_packer_axis_stall errors=%0d", errors);
    $fatal(1);
  end

endmodule
