// telemetry_counter.v
//
// Enhanced telemetry counter for Waveform Brain v1 with windowed measurement.
// This module counts syndrome flips across multiple decoder channels. A flip
// occurs when the two-bit syndrome for a channel changes between successive
// valid samples. The counter supports windowed measurement triggered via
// control signals and also maintains a running total of flips. The design
// exposes status flags to indicate whether a measurement window is active or
// complete.

module telemetry_counter (
    input  logic         clk,
    input  logic         rst_n,
    // Per‑channel valid and syndrome inputs
    input  logic  [3:0]  valid_in,
    input  logic  [1:0]  syndrome [0:3],
    // Control registers
    input  logic         start_sample,      // Pulse to begin a measurement window
    input  logic         clear_total,       // Clears the running total flips
    input  logic [31:0]  window_cycles,     // Number of clock cycles in a measurement window
    // Status outputs
    output logic         sample_active,     // High while window is in progress
    output logic         sample_done,       // Pulses high for one cycle when window completes
    // Sample result outputs
    output logic [31:0]  flips_delta,       // Number of flips detected during the last window
    output logic [31:0]  total_flips        // Running total of all flips (saturating)
);

    // Storage for last syndrome per channel
    logic [1:0] last_syndrome [0:3];
    // Accumulators
    logic [31:0] delta_count;
    logic [31:0] total_count;
    // Window management
    logic [31:0] window_counter;
    logic [31:0] window_last;
    logic        sample_active_reg;
    logic        sample_done_reg;
    logic        start_prev;

    always_comb begin
        // A programmed value of 0 is treated as a 1-cycle window.
        window_last = (window_cycles == 32'd0) ? 32'd0 : (window_cycles - 32'd1);
    end

    // Telemetry and window management.  A single always_ff block updates the
    // last_syndrome memory, counts flips when the sample window is active,
    // manages the measurement window timing, and accumulates the running total.
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // Reset state
            last_syndrome[0]   <= 2'b00;
            last_syndrome[1]   <= 2'b00;
            last_syndrome[2]   <= 2'b00;
            last_syndrome[3]   <= 2'b00;
            delta_count        <= 32'h0;
            total_count        <= 32'h0;
            window_counter     <= 32'h0;
            sample_active_reg  <= 1'b0;
            sample_done_reg    <= 1'b0;
            start_prev         <= 1'b0;
            flips_delta        <= 32'h0;
        end else begin
            // Default: clear sample_done pulse
            sample_done_reg <= 1'b0;

            // Rising edge detection for start_sample to begin a new window
            start_prev <= start_sample;

            // Clear total counter if commanded
            if (clear_total) begin
                total_count <= 32'h0;
            end

            // If a new window is requested while no window is active
            if (!sample_active_reg && (start_sample && !start_prev)) begin
                sample_active_reg <= 1'b1;
                delta_count      <= 32'h0;
                window_counter   <= 32'h0;
            end

            // During an active window, accumulate flips and advance window counter
            if (sample_active_reg) begin
                // Detect flips across all channels in this cycle
                integer i;
                logic [2:0] flip_sum;
                logic [31:0] delta_next;
                flip_sum = 3'd0;
                for (i = 0; i < 4; i++) begin
                    // A flip is counted only when the channel asserts valid
                    // and the syndrome changes relative to the last sampled value
                    if (valid_in[i]) begin
                        if (syndrome[i] != last_syndrome[i]) begin
                            flip_sum = flip_sum + 1;
                        end
                        // Update last_syndrome for next detection
                        last_syndrome[i] <= syndrome[i];
                    end
                end
                // Accumulate delta_count with saturation
                if (delta_count <= (32'hFFFFFFFF - flip_sum)) begin
                    delta_next = delta_count + flip_sum;
                end else begin
                    delta_next = 32'hFFFFFFFF;
                end
                delta_count <= delta_next;
                // Increment window counter
                window_counter <= window_counter + 1;
                // Check for end of window
                if (window_counter >= window_last) begin
                    // Window completed
                    sample_active_reg <= 1'b0;
                    sample_done_reg   <= 1'b1;
                    flips_delta       <= delta_next;
                    // Accumulate into total_count unless a clear command is pending
                    if (!clear_total) begin
                        if (total_count <= (32'hFFFFFFFF - delta_next)) begin
                            total_count <= total_count + delta_next;
                        end else begin
                            total_count <= 32'hFFFFFFFF;
                        end
                    end
                end
            end else begin
                // When window is not active, update last_syndrome only when valid
                integer j;
                for (j = 0; j < 4; j++) begin
                    if (valid_in[j]) begin
                        last_syndrome[j] <= syndrome[j];
                    end
                end
            end
        end
    end

    // Output assignments
    assign sample_active  = sample_active_reg;
    assign sample_done    = sample_done_reg;
    assign total_flips    = total_count;
    // flips_delta is latched in the always_ff above when the window ends
endmodule