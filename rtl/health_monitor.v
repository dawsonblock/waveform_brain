// health_monitor.v
//
// Event-rate health monitor for Waveform Brain v1.0.
//
// This block turns sticky or transient runtime events into saturating counters.
// A sticky fault is useful for safety, but a counter is better for diagnosis:
// one event may be transient, repeated events indicate throughput, timing,
// signal-integrity, or calibration problems.
//
// Counters clear synchronously when clear is asserted.

module health_monitor (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        clear,

    // Fault / runtime event inputs
    input  logic        safety_fault_latched,
    input  logic        safety_kill,
    input  logic        axis_tvalid,
    input  logic        axis_tready,
    input  logic [3:0]  decoder_valid,
    input  logic        telemetry_sample_active,
    input  logic        telemetry_sample_done,

    // Saturating event counters
    output logic [31:0] safety_trip_count,
    output logic [31:0] axis_stall_cycle_count,
    output logic [31:0] decoder_valid_cycle_count,
    output logic [31:0] telemetry_window_done_count,

    // Compact status bits
    output logic [31:0] health_status
);

    logic safety_fault_d;

    function automatic [31:0] sat_inc(input [31:0] value);
        if (value == 32'hFFFF_FFFF) begin
            sat_inc = 32'hFFFF_FFFF;
        end else begin
            sat_inc = value + 32'd1;
        end
    endfunction

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            safety_fault_d              <= 1'b0;
            safety_trip_count           <= 32'd0;
            axis_stall_cycle_count      <= 32'd0;
            decoder_valid_cycle_count   <= 32'd0;
            telemetry_window_done_count <= 32'd0;
        end else begin
            safety_fault_d <= safety_fault_latched;

            if (clear) begin
                safety_trip_count           <= 32'd0;
                axis_stall_cycle_count      <= 32'd0;
                decoder_valid_cycle_count   <= 32'd0;
                telemetry_window_done_count <= 32'd0;
            end else begin
                // Count rising edge of the sticky safety fault.
                if (safety_fault_latched && !safety_fault_d) begin
                    safety_trip_count <= sat_inc(safety_trip_count);
                end

                // Count cycles where an AXI-Stream payload is available but stalled.
                if (axis_tvalid && !axis_tready) begin
                    axis_stall_cycle_count <= sat_inc(axis_stall_cycle_count);
                end

                // Count cycles where at least one decoder lane emits valid output.
                if (|decoder_valid) begin
                    decoder_valid_cycle_count <= sat_inc(decoder_valid_cycle_count);
                end

                // Count completed telemetry windows.
                if (telemetry_sample_done) begin
                    telemetry_window_done_count <= sat_inc(telemetry_window_done_count);
                end
            end
        end
    end

    // Bitfield:
    // bit0 safety_fault_latched
    // bit1 safety_kill
    // bit2 axis_backpressure_now
    // bit3 any_decoder_valid
    // bit4 telemetry_sample_active
    // bit5 telemetry_sample_done
    // bits31:6 reserved
    always_comb begin
        health_status = 32'd0;
        health_status[0] = safety_fault_latched;
        health_status[1] = safety_kill;
        health_status[2] = axis_tvalid && !axis_tready;
        health_status[3] = |decoder_valid;
        health_status[4] = telemetry_sample_active;
        health_status[5] = telemetry_sample_done;
    end

endmodule
