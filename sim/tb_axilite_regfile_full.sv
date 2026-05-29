`timescale 1ns/1ps

module tb_axilite_regfile_full;
  logic clk = 1'b0;
  logic rst_n = 1'b0;

  logic [7:0]  awaddr;
  logic        awvalid;
  logic        awready;

  logic [31:0] wdata;
  logic [3:0]  wstrb;
  logic        wvalid;
  logic        wready;

  logic [1:0]  bresp;
  logic        bvalid;
  logic        bready;

  logic [7:0]  araddr;
  logic        arvalid;
  logic        arready;

  logic [31:0] rdata;
  logic [1:0]  rresp;
  logic        rvalid;
  logic        rready;

  logic                         prbs_enable;
  logic signed [31:0]           inv_delta_q;
  logic signed [31:0]           delta_adc_q;
  logic signed [31:0]           coeffs [0:3];
  logic [15:0]                  alpha;
  logic [15:0]                  kill_threshold;
  logic                         clear_faults;

  logic [15:0]                  status_word_in;
  logic [15:0]                  fault_flags_in;
  logic [31:0]                  build_id;

  logic [31:0]                  telemetry_flips_delta_in;
  logic [31:0]                  telemetry_total_flips_in;
  logic                         telemetry_sample_active_in;
  logic                         telemetry_sample_done_in;

  logic [31:0]                  health_status_in;
  logic [31:0]                  health_safety_trip_count_in;
  logic [31:0]                  health_axis_stall_count_in;
  logic [31:0]                  health_decoder_valid_count_in;
  logic [31:0]                  health_telem_done_count_in;

  logic [4:0]                   axis_fifo_level_in;
  logic [31:0]                  axis_fifo_overflow_count_in;
  logic [31:0]                  axis_fifo_stall_count_in;
  logic [31:0]                  axis_frame_drop_count_in;
  logic [31:0]                  axis_sequence_count_in;

  logic                         telem_start_sample;
  logic                         telem_clear_total;
  logic [31:0]                  telem_window_cycles;
  logic                         cfg_update_pulse;

  int errors = 0;
  int cfg_pulse_count = 0;

  localparam [1:0] AXI_OKAY = 2'b00;
  localparam [1:0] AXI_SLVERR = 2'b10;

  always #5 clk = ~clk;

  always_ff @(posedge clk) begin
    if (cfg_update_pulse) begin
      cfg_pulse_count <= cfg_pulse_count + 1;
    end
  end

  axilite_regfile_full dut (
      .s_axi_aclk(clk),
      .s_axi_aresetn(rst_n),
      .s_axi_awaddr(awaddr),
      .s_axi_awvalid(awvalid),
      .s_axi_awready(awready),
      .s_axi_wdata(wdata),
      .s_axi_wstrb(wstrb),
      .s_axi_wvalid(wvalid),
      .s_axi_wready(wready),
      .s_axi_bresp(bresp),
      .s_axi_bvalid(bvalid),
      .s_axi_bready(bready),
      .s_axi_araddr(araddr),
      .s_axi_arvalid(arvalid),
      .s_axi_arready(arready),
      .s_axi_rdata(rdata),
      .s_axi_rresp(rresp),
      .s_axi_rvalid(rvalid),
      .s_axi_rready(rready),
      .prbs_enable(prbs_enable),
      .inv_delta_q(inv_delta_q),
      .delta_adc_q(delta_adc_q),
      .coeffs(coeffs),
      .alpha(alpha),
      .kill_threshold(kill_threshold),
      .clear_faults(clear_faults),
      .status_word_in(status_word_in),
      .fault_flags_in(fault_flags_in),
      .build_id(build_id),
      .telemetry_flips_delta_in(telemetry_flips_delta_in),
      .telemetry_total_flips_in(telemetry_total_flips_in),
      .telemetry_sample_active_in(telemetry_sample_active_in),
      .telemetry_sample_done_in(telemetry_sample_done_in),
      .health_status_in(health_status_in),
      .health_safety_trip_count_in(health_safety_trip_count_in),
      .health_axis_stall_count_in(health_axis_stall_count_in),
      .health_decoder_valid_count_in(health_decoder_valid_count_in),
      .health_telem_done_count_in(health_telem_done_count_in),
      .axis_fifo_level_in(axis_fifo_level_in),
      .axis_fifo_overflow_count_in(axis_fifo_overflow_count_in),
      .axis_fifo_stall_count_in(axis_fifo_stall_count_in),
      .axis_frame_drop_count_in(axis_frame_drop_count_in),
      .axis_sequence_count_in(axis_sequence_count_in),
      .telem_start_sample(telem_start_sample),
      .telem_clear_total(telem_clear_total),
      .telem_window_cycles(telem_window_cycles),
      .cfg_update_pulse(cfg_update_pulse)
  );

  task automatic reset_bus_inputs;
    begin
      awaddr = 8'h00;
      awvalid = 1'b0;
      wdata = 32'h0;
      wstrb = 4'h0;
      wvalid = 1'b0;
      bready = 1'b0;
      araddr = 8'h00;
      arvalid = 1'b0;
      rready = 1'b0;
    end
  endtask

  task automatic axil_write(
      input [7:0] addr,
      input [31:0] data,
      input [3:0] strobe,
      input integer order_mode,
      input integer bstall,
      output [1:0] resp_out
  );
    begin
      if (order_mode == 0) begin
        awaddr = addr;
        awvalid = 1'b1;
        while (!awready) @(posedge clk);
        @(posedge clk);
        awvalid = 1'b0;

        wdata = data;
        wstrb = strobe;
        wvalid = 1'b1;
        while (!wready) @(posedge clk);
        @(posedge clk);
        wvalid = 1'b0;
      end else if (order_mode == 1) begin
        wdata = data;
        wstrb = strobe;
        wvalid = 1'b1;
        while (!wready) @(posedge clk);
        @(posedge clk);
        wvalid = 1'b0;

        awaddr = addr;
        awvalid = 1'b1;
        while (!awready) @(posedge clk);
        @(posedge clk);
        awvalid = 1'b0;
      end else begin
        awaddr = addr;
        awvalid = 1'b1;
        wdata = data;
        wstrb = strobe;
        wvalid = 1'b1;
        while (!(awready && wready)) @(posedge clk);
        @(posedge clk);
        awvalid = 1'b0;
        wvalid = 1'b0;
      end

      bready = 1'b0;
      repeat (bstall) @(posedge clk);
      bready = 1'b1;
      while (!bvalid) @(posedge clk);
      resp_out = bresp;
      @(posedge clk);
      bready = 1'b0;
    end
  endtask

  task automatic axil_read(
      input [7:0] addr,
      input integer rstall,
      output [31:0] data_out,
      output [1:0] resp_out
  );
    begin
      araddr = addr;
      arvalid = 1'b1;
      while (!arready) @(posedge clk);
      @(posedge clk);
      arvalid = 1'b0;

      rready = 1'b0;
      repeat (rstall) @(posedge clk);
      rready = 1'b1;
      while (!rvalid) @(posedge clk);
      data_out = rdata;
      resp_out = rresp;
      @(posedge clk);
      rready = 1'b0;
    end
  endtask

  task automatic check_eq32(
      input [31:0] got,
      input [31:0] exp,
      input [255:0] msg
  );
    begin
      if (got !== exp) begin
        $display("FAIL %s got=%h exp=%h", msg, got, exp);
        errors = errors + 1;
      end
    end
  endtask

  task automatic check_eq2(
      input [1:0] got,
      input [1:0] exp,
      input [255:0] msg
  );
    begin
      if (got !== exp) begin
        $display("FAIL %s got=%b exp=%b", msg, got, exp);
        errors = errors + 1;
      end
    end
  endtask

  initial begin
    logic [1:0] wr_resp;
    logic [1:0] rd_resp;
    logic [31:0] rd_data;
    logic [31:0] expected_inv_delta;

    reset_bus_inputs();

    status_word_in = 16'h0000;
    fault_flags_in = 16'h0000;
    build_id = 32'h5742_5631;
    telemetry_flips_delta_in = 32'h0;
    telemetry_total_flips_in = 32'h0;
    telemetry_sample_active_in = 1'b0;
    telemetry_sample_done_in = 1'b0;
    health_status_in = 32'h0;
    health_safety_trip_count_in = 32'h0;
    health_axis_stall_count_in = 32'h0;
    health_decoder_valid_count_in = 32'h0;
    health_telem_done_count_in = 32'h0;
    axis_fifo_level_in = 5'd0;
    axis_fifo_overflow_count_in = 32'h0;
    axis_fifo_stall_count_in = 32'h0;
    axis_frame_drop_count_in = 32'h0;
    axis_sequence_count_in = 32'h0;

    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    expected_inv_delta = 32'h0001_0000;
    check_eq32(inv_delta_q, expected_inv_delta, "default active inv_delta_q");

    axil_write(8'h10, 32'h0002_1234, 4'hF, 0, 0, wr_resp);
    check_eq2(wr_resp, AXI_OKAY, "AW-before-W write response");
    check_eq32(inv_delta_q, expected_inv_delta, "active unchanged before apply");

    axil_read(8'h10, 0, rd_data, rd_resp);
    check_eq2(rd_resp, AXI_OKAY, "read staged register response");
    check_eq32(rd_data, 32'h0002_1234, "staged value readable");

    axil_write(8'h10, 32'hABCD_9876, 4'hF, 1, 0, wr_resp);
    check_eq2(wr_resp, AXI_OKAY, "W-before-AW write response");
    axil_read(8'h10, 0, rd_data, rd_resp);
    check_eq32(rd_data, 32'hABCD_9876, "W-before-AW staged readback");

    axil_write(8'h10, 32'h1234_5678, 4'h3, 2, 0, wr_resp);
    check_eq2(wr_resp, AXI_OKAY, "partial write response");
    axil_read(8'h10, 0, rd_data, rd_resp);
    check_eq32(rd_data, 32'hABCD_5678, "partial write preserved upper bytes");

    axil_write(8'h70, 32'h0000_0001, 4'hF, 2, 0, wr_resp);
    check_eq2(wr_resp, AXI_OKAY, "cfg apply response");
    expected_inv_delta = 32'hABCD_5678;
    check_eq32(inv_delta_q, expected_inv_delta, "active updates after apply");

    // Invalid write should return SLVERR.
    axil_write(8'h74, 32'h0000_0001, 4'hF, 2, 0, wr_resp);
    check_eq2(wr_resp, AXI_SLVERR, "invalid write response");

    // Invalid read should return SLVERR.
    axil_read(8'h74, 0, rd_data, rd_resp);
    check_eq2(rd_resp, AXI_SLVERR, "invalid read response");

    // B-channel backpressure should block new AW/W acceptance and not
    // double-fire cfg_update_pulse.
    axil_write(8'h10, 32'h0003_0000, 4'hF, 2, 0, wr_resp);
    check_eq2(wr_resp, AXI_OKAY, "stage before backpressure test");

    awaddr = 8'h70;
    awvalid = 1'b1;
    wdata = 32'h0000_0001;
    wstrb = 4'hF;
    wvalid = 1'b1;
    while (!(awready && wready)) @(posedge clk);
    @(posedge clk);
    awvalid = 1'b0;
    wvalid = 1'b0;

    bready = 1'b0;
    repeat (3) begin
      awaddr = 8'h10;
      awvalid = 1'b1;
      wdata = 32'hFFFF_FFFF;
      wstrb = 4'hF;
      wvalid = 1'b1;
      @(posedge clk);
      if (awready || wready) begin
        $display("FAIL accepted AW/W while BVALID backpressured");
        errors = errors + 1;
      end
    end
    awvalid = 1'b0;
    wvalid = 1'b0;

    bready = 1'b1;
    while (!bvalid) @(posedge clk);
    @(posedge clk);
    bready = 1'b0;

    if (cfg_pulse_count !== 2) begin
      $display("FAIL cfg_update_pulse count got=%0d exp=2", cfg_pulse_count);
      errors = errors + 1;
    end

    if (errors == 0) begin
      $display("TB_PASS tb_axilite_regfile_full");
      $finish;
    end

    $display("TB_FAIL tb_axilite_regfile_full errors=%0d", errors);
    $fatal(1);
  end

endmodule
