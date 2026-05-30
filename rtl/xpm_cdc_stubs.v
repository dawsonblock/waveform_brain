// Behavioral simulation models for Xilinx XPM CDC primitives used in this project.
//
// These are NOT bit-accurate replacements for the real XPMs and they do not model
// metastability. They DO model the structural behavior that matters for catching
// CDC integration bugs in simulation:
//
//   - xpm_cdc_single / xpm_cdc_array_single: N-flop synchronizer chain in the
//     destination clock domain, optional source-side input register.
//   - xpm_cdc_pulse: source-side toggle, destination-side sync chain, edge
//     detector to recover a one-cycle pulse.
//   - xpm_cdc_gray: source binary->gray register, destination N-flop sync chain,
//     destination gray->binary, optional destination output register.
//   - xpm_cdc_handshake: full toggle-based request/acknowledge handshake with
//     data held stable in the source domain while a transaction is in flight.
//
// For real CDC sign-off, replace this file with the actual Xilinx XPM library
// in your synthesis flow.

// ----------------------------------------------------------------------------
// xpm_cdc_handshake -- multi-bit data with req/ack handshake (auto-ack mode).
// ----------------------------------------------------------------------------
module xpm_cdc_handshake #(
    parameter [31:0] DEST_EXT_HSK   = 0,
    parameter [31:0] DEST_SYNC_FF   = 2,
    parameter [31:0] INIT_SYNC_FF   = 0,
    parameter [31:0] SIM_ASSERT_CHK = 0,
    parameter [31:0] SRC_SYNC_FF    = 2,
    parameter [31:0] WIDTH          = 1
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
    localparam integer DEST_FF = (DEST_SYNC_FF < 2) ? 2 : DEST_SYNC_FF;
    localparam integer SRC_FF  = (SRC_SYNC_FF  < 2) ? 2 : SRC_SYNC_FF;

    // -------- source domain: data latch + req toggle --------
    reg                 src_busy;
    reg                 src_req_toggle;
    reg [WIDTH-1:0]     src_data;
    initial begin
        src_busy       = 1'b0;
        src_req_toggle = 1'b0;
        src_data       = {WIDTH{1'b0}};
    end

    // -------- destination domain: sync req toggle, edge detect, sample --------
    reg [DEST_FF-1:0]   req_sync;
    reg                 dest_prev_toggle;
    reg [WIDTH-1:0]     dest_data_reg;
    reg                 dest_req_reg;
    reg                 dest_ack_toggle;
    initial begin
        req_sync         = {DEST_FF{1'b0}};
        dest_prev_toggle = 1'b0;
        dest_data_reg    = {WIDTH{1'b0}};
        dest_req_reg     = 1'b0;
        dest_ack_toggle  = 1'b0;
    end

    wire dest_req_edge = req_sync[DEST_FF-1] ^ dest_prev_toggle;

    always @(posedge dest_clk) begin
        req_sync         <= {req_sync[DEST_FF-2:0], src_req_toggle};
        dest_prev_toggle <= req_sync[DEST_FF-1];
        if (dest_req_edge) begin
            // Data is held stable in src_data while busy; safe to sample now.
            dest_data_reg   <= src_data;
            dest_req_reg    <= 1'b1;
            dest_ack_toggle <= ~dest_ack_toggle;
        end else begin
            dest_req_reg    <= 1'b0;
        end
    end

    assign dest_out = dest_data_reg;
    assign dest_req = dest_req_reg;
    assign dest_ack = dest_req_reg;

    // -------- source domain: sync ack toggle back, clear busy, pulse src_rcv --------
    reg [SRC_FF-1:0]    ack_sync;
    reg                 src_prev_ack_toggle;
    reg                 src_rcv_reg;
    initial begin
        ack_sync            = {SRC_FF{1'b0}};
        src_prev_ack_toggle = 1'b0;
        src_rcv_reg         = 1'b0;
    end

    wire src_ack_edge = ack_sync[SRC_FF-1] ^ src_prev_ack_toggle;

    always @(posedge src_clk) begin
        ack_sync            <= {ack_sync[SRC_FF-2:0], dest_ack_toggle};
        src_prev_ack_toggle <= ack_sync[SRC_FF-1];
        src_rcv_reg         <= src_ack_edge;

        // Ack edge clears busy; an accepted send sets it. Source order matters
        // under nonblocking assignment (last writer wins): the send-accept block
        // is intentionally last so a same-cycle new transaction wins.
        if (src_ack_edge) begin
            src_busy <= 1'b0;
        end
        if (src_send && !src_busy) begin
            src_data       <= src_in;
            src_req_toggle <= ~src_req_toggle;
            src_busy       <= 1'b1;
        end
    end

    assign src_rcv = src_rcv_reg;

    // Silence "unused parameter" lint warnings.
    wire _unused_param_ok = (|DEST_EXT_HSK) ^ (|INIT_SYNC_FF) ^ (|SIM_ASSERT_CHK);
endmodule

// ----------------------------------------------------------------------------
// xpm_cdc_pulse -- single-cycle pulse synchronizer (toggle method).
// ----------------------------------------------------------------------------
module xpm_cdc_pulse #(
    parameter [31:0] DEST_SYNC_FF   = 2,
    parameter [31:0] INIT_SYNC_FF   = 0,
    parameter [31:0] REG_OUTPUT     = 0,
    parameter [31:0] RST_USED       = 0,
    parameter [31:0] SIM_ASSERT_CHK = 0
) (
    input  wire src_clk,
    input  wire src_pulse,
    input  wire dest_clk,
    output wire dest_pulse
);
    localparam integer SYNC_FF = (DEST_SYNC_FF < 2) ? 2 : DEST_SYNC_FF;

    reg src_toggle;
    initial src_toggle = 1'b0;
    always @(posedge src_clk) begin
        if (src_pulse) src_toggle <= ~src_toggle;
    end

    reg [SYNC_FF-1:0] sync_chain;
    initial sync_chain = {SYNC_FF{1'b0}};
    always @(posedge dest_clk) begin
        sync_chain <= {sync_chain[SYNC_FF-2:0], src_toggle};
    end

    reg dest_prev_toggle;
    initial dest_prev_toggle = 1'b0;
    always @(posedge dest_clk) dest_prev_toggle <= sync_chain[SYNC_FF-1];

    wire pulse_comb = sync_chain[SYNC_FF-1] ^ dest_prev_toggle;

    reg pulse_reg;
    initial pulse_reg = 1'b0;
    always @(posedge dest_clk) pulse_reg <= pulse_comb;

    assign dest_pulse = (REG_OUTPUT != 0) ? pulse_reg : pulse_comb;

    wire _unused_param_ok =
        (|INIT_SYNC_FF) ^ (|RST_USED) ^ (|SIM_ASSERT_CHK);
endmodule

// ----------------------------------------------------------------------------
// xpm_cdc_single -- single-bit N-flop synchronizer.
// ----------------------------------------------------------------------------
module xpm_cdc_single #(
    parameter [31:0] DEST_SYNC_FF   = 2,
    parameter [31:0] INIT_SYNC_FF   = 0,
    parameter [31:0] SIM_ASSERT_CHK = 0,
    parameter [31:0] SRC_INPUT_REG  = 0
) (
    input  wire src_clk,
    input  wire src_in,
    input  wire dest_clk,
    output wire dest_out
);
    localparam integer SYNC_FF = (DEST_SYNC_FF < 2) ? 2 : DEST_SYNC_FF;

    reg src_reg;
    initial src_reg = 1'b0;
    always @(posedge src_clk) src_reg <= src_in;

    wire src_sample = (SRC_INPUT_REG != 0) ? src_reg : src_in;

    reg [SYNC_FF-1:0] sync_chain;
    initial sync_chain = {SYNC_FF{1'b0}};
    always @(posedge dest_clk) begin
        sync_chain <= {sync_chain[SYNC_FF-2:0], src_sample};
    end

    assign dest_out = sync_chain[SYNC_FF-1];

    wire _unused_param_ok = (|INIT_SYNC_FF) ^ (|SIM_ASSERT_CHK);
endmodule

// ----------------------------------------------------------------------------
// xpm_cdc_array_single -- vector of independent single-bit synchronizers.
// Per Xilinx semantics, bits are NOT coherent across the crossing.
// ----------------------------------------------------------------------------
module xpm_cdc_array_single #(
    parameter [31:0] DEST_SYNC_FF   = 2,
    parameter [31:0] INIT_SYNC_FF   = 0,
    parameter [31:0] SIM_ASSERT_CHK = 0,
    parameter [31:0] SRC_INPUT_REG  = 0,
    parameter [31:0] WIDTH          = 1
) (
    input  wire             src_clk,
    input  wire [WIDTH-1:0] src_in,
    input  wire             dest_clk,
    output wire [WIDTH-1:0] dest_out
);
    localparam integer SYNC_FF = (DEST_SYNC_FF < 2) ? 2 : DEST_SYNC_FF;

    reg [WIDTH-1:0] src_reg;
    initial src_reg = {WIDTH{1'b0}};
    always @(posedge src_clk) src_reg <= src_in;

    wire [WIDTH-1:0] src_sample = (SRC_INPUT_REG != 0) ? src_reg : src_in;

    reg [WIDTH-1:0] sync_chain [0:SYNC_FF-1];
    integer i;
    initial begin
        for (i = 0; i < SYNC_FF; i = i + 1) sync_chain[i] = {WIDTH{1'b0}};
    end

    always @(posedge dest_clk) begin
        sync_chain[0] <= src_sample;
        for (i = 1; i < SYNC_FF; i = i + 1) begin
            sync_chain[i] <= sync_chain[i-1];
        end
    end

    assign dest_out = sync_chain[SYNC_FF-1];

    wire _unused_param_ok = (|INIT_SYNC_FF) ^ (|SIM_ASSERT_CHK);
endmodule

// ----------------------------------------------------------------------------
// xpm_cdc_gray -- gray-coded vector synchronizer for monotonic counters.
// ----------------------------------------------------------------------------
module xpm_cdc_gray #(
    parameter [31:0] DEST_SYNC_FF   = 2,
    parameter [31:0] INIT_SYNC_FF   = 0,
    parameter [31:0] REG_OUTPUT     = 0,
    parameter [31:0] SIM_ASSERT_CHK = 0,
    parameter [31:0] WIDTH          = 1
) (
    input  wire             src_clk,
    input  wire [WIDTH-1:0] src_in_bin,
    input  wire             dest_clk,
    output wire [WIDTH-1:0] dest_out_bin
);
    localparam integer SYNC_FF = (DEST_SYNC_FF < 2) ? 2 : DEST_SYNC_FF;

    function automatic [WIDTH-1:0] bin2gray;
        input [WIDTH-1:0] b;
        begin
            bin2gray = b ^ (b >> 1);
        end
    endfunction

    function automatic [WIDTH-1:0] gray2bin;
        input [WIDTH-1:0] g;
        integer k;
        reg [WIDTH-1:0] b;
        begin
            b = g;
            for (k = 1; k < WIDTH; k = k + 1) begin
                b = b ^ (g >> k);
            end
            gray2bin = b;
        end
    endfunction

    reg [WIDTH-1:0] gray_src;
    initial gray_src = {WIDTH{1'b0}};
    always @(posedge src_clk) gray_src <= bin2gray(src_in_bin);

    reg [WIDTH-1:0] sync_chain [0:SYNC_FF-1];
    integer i;
    initial begin
        for (i = 0; i < SYNC_FF; i = i + 1) sync_chain[i] = {WIDTH{1'b0}};
    end

    always @(posedge dest_clk) begin
        sync_chain[0] <= gray_src;
        for (i = 1; i < SYNC_FF; i = i + 1) begin
            sync_chain[i] <= sync_chain[i-1];
        end
    end

    wire [WIDTH-1:0] gray_at_dest = sync_chain[SYNC_FF-1];
    wire [WIDTH-1:0] bin_at_dest  = gray2bin(gray_at_dest);

    reg [WIDTH-1:0] bin_reg;
    initial bin_reg = {WIDTH{1'b0}};
    always @(posedge dest_clk) bin_reg <= bin_at_dest;

    assign dest_out_bin = (REG_OUTPUT != 0) ? bin_reg : bin_at_dest;

    wire _unused_param_ok = (|INIT_SYNC_FF) ^ (|SIM_ASSERT_CHK);
endmodule
