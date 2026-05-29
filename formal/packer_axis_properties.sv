// packer_axis_properties.sv
//
// Bindable AXI4-Stream protocol properties for packer_axis.
// Intended for simulation/formal lint flows. Not included in synthesis.

module packer_axis_properties (
    input logic        clk,
    input logic        rst_n,
    input logic [63:0] m_axis_tdata,
    input logic        m_axis_tvalid,
    input logic        m_axis_tready,
    input logic        m_axis_tlast
);

    // Once valid is asserted and the downstream is not ready, payload and TLAST
    // must remain stable until a transfer occurs.
    property p_axis_hold_when_stalled;
        @(posedge clk) disable iff (!rst_n)
            (m_axis_tvalid && !m_axis_tready) |=> (
                m_axis_tvalid &&
                $stable(m_axis_tdata) &&
                $stable(m_axis_tlast)
            );
    endproperty

    assert property (p_axis_hold_when_stalled);

    // TLAST may only be observed on a valid beat.
    property p_tlast_implies_valid;
        @(posedge clk) disable iff (!rst_n)
            m_axis_tlast |-> m_axis_tvalid;
    endproperty

    assert property (p_tlast_implies_valid);

endmodule

// Example bind line for a formal/simulation harness:
// bind packer_axis packer_axis_properties u_packer_axis_props (
//     .clk(clk),
//     .rst_n(rst_n),
//     .m_axis_tdata(m_axis_tdata),
//     .m_axis_tvalid(m_axis_tvalid),
//     .m_axis_tready(m_axis_tready),
//     .m_axis_tlast(m_axis_tlast)
// );
