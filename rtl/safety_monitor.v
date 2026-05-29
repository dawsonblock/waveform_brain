`timescale 1ns/1ps

// safety_monitor.v
// Monitors the ADC values for over‑range conditions and triggers a safety
// kill signal when a configurable threshold is exceeded. Faults are
// latched until cleared by clear_faults. Additional variance monitoring
// can be added in a future version.


module safety_monitor #(
module safety_monitor #(
    parameter int ADC_WIDTH = 16
)(
    input  logic                     clk,
    input  logic                     rst_n,
    input  logic signed [ADC_WIDTH-1:0] adc_in,
    input  logic [ADC_WIDTH-1:0]     kill_threshold,
    input  logic                     clear_faults,
    output logic                     safety_kill,
    output logic                     fault_latched
);
    logic signed [ADC_WIDTH:0] adc_ext;
    logic [ADC_WIDTH:0] adc_mag;

    always_comb begin
        adc_ext = {adc_in[ADC_WIDTH-1], adc_in};
        if (adc_ext < 0) begin
            adc_mag = $unsigned(-adc_ext);
        end else begin
            adc_mag = $unsigned(adc_ext);
        end
    end

    // Latch fault when over threshold
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fault_latched <= 1'b0;
        end else if (clear_faults) begin
            fault_latched <= 1'b0;
        end else begin
            if (adc_mag > {1'b0, kill_threshold}) begin
                fault_latched <= 1'b1;
            end
        end
    end
    // Active-high kill signal when fault latched
    assign safety_kill = fault_latched;

endmodule