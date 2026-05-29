// Lint stubs for Xilinx XPM CDC primitives used in this project.
// These stubs are for lint/simulation convenience only.

module xpm_cdc_handshake #(
    parameter int DEST_EXT_HSK = 0,
    parameter int DEST_SYNC_FF = 2,
    parameter int INIT_SYNC_FF = 0,
    parameter int SIM_ASSERT_CHK = 0,
    parameter int SRC_SYNC_FF = 2,
    parameter int WIDTH = 1
) (
    input  wire             src_clk,
    input  wire [WIDTH-1:0] src_in,
    input  wire             src_send,
    output wire             src_rcv,
    input  wire             dest_clk,
    output wire [WIDTH-1:0] dest_out,
    output wire             dest_req,
    output wire             dest_ack
);
    assign src_rcv = src_send;
    assign dest_out = src_in;
    assign dest_req = src_send;
    assign dest_ack = src_send;
    wire _unused_ok = src_clk ^ dest_clk;
    wire _unused_param_ok =
        DEST_EXT_HSK ^ DEST_SYNC_FF ^ INIT_SYNC_FF ^ SIM_ASSERT_CHK ^ SRC_SYNC_FF;
endmodule

module xpm_cdc_pulse #(
    parameter int DEST_SYNC_FF = 2,
    parameter int INIT_SYNC_FF = 0,
    parameter int REG_OUTPUT = 0,
    parameter int RST_USED = 0,
    parameter int SIM_ASSERT_CHK = 0
) (
    input  wire src_clk,
    input  wire src_pulse,
    input  wire dest_clk,
    output wire dest_pulse
);
    assign dest_pulse = src_pulse;
    wire _unused_ok = src_clk ^ dest_clk;
    wire _unused_param_ok =
        DEST_SYNC_FF ^ INIT_SYNC_FF ^ REG_OUTPUT ^ RST_USED ^ SIM_ASSERT_CHK;
endmodule

module xpm_cdc_single #(
    parameter int DEST_SYNC_FF = 2,
    parameter int INIT_SYNC_FF = 0,
    parameter int SIM_ASSERT_CHK = 0,
    parameter int SRC_INPUT_REG = 0
) (
    input  wire src_clk,
    input  wire src_in,
    input  wire dest_clk,
    output wire dest_out
);
    assign dest_out = src_in;
    wire _unused_ok = src_clk ^ dest_clk;
    wire _unused_param_ok = DEST_SYNC_FF ^ INIT_SYNC_FF ^ SIM_ASSERT_CHK ^ SRC_INPUT_REG;
endmodule

module xpm_cdc_array_single #(
    parameter int DEST_SYNC_FF = 2,
    parameter int INIT_SYNC_FF = 0,
    parameter int SIM_ASSERT_CHK = 0,
    parameter int SRC_INPUT_REG = 0,
    parameter int WIDTH = 1
) (
    input  wire             src_clk,
    input  wire [WIDTH-1:0] src_in,
    input  wire             dest_clk,
    output wire [WIDTH-1:0] dest_out
);
    assign dest_out = src_in;
    wire _unused_ok = src_clk ^ dest_clk;
    wire _unused_param_ok = DEST_SYNC_FF ^ INIT_SYNC_FF ^ SIM_ASSERT_CHK ^ SRC_INPUT_REG;
endmodule

module xpm_cdc_gray #(
    parameter int DEST_SYNC_FF = 2,
    parameter int INIT_SYNC_FF = 0,
    parameter int REG_OUTPUT = 0,
    parameter int SIM_ASSERT_CHK = 0,
    parameter int WIDTH = 1
) (
    input  wire             src_clk,
    input  wire [WIDTH-1:0] src_in_bin,
    input  wire             dest_clk,
    output wire [WIDTH-1:0] dest_out_bin
);
    assign dest_out_bin = src_in_bin;
    wire _unused_ok = src_clk ^ dest_clk;
    wire _unused_param_ok = DEST_SYNC_FF ^ INIT_SYNC_FF ^ REG_OUTPUT ^ SIM_ASSERT_CHK;
endmodule
