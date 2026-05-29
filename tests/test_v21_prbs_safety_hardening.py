import unittest
from pathlib import Path


class TestV21PrbsSafetyHardening(unittest.TestCase):
    def test_top_has_prbs_effective_adc_mux(self):
        text = Path("rtl/waveform_control_4q_top.v").read_text()
        self.assertIn(
            "logic signed [ADC_WIDTH-1:0] effective_adc [0:3];",
            text,
        )
        self.assertIn(
            "assign effective_adc[ch] = prbs_enable ? " "prbs_sample : adc_in[ch];",
            text,
        )
        self.assertIn(".prbs_out(prbs_word)", text)

    def test_decoder_uses_effective_adc(self):
        text = Path("rtl/waveform_control_4q_top.v").read_text()
        self.assertIn(".adc_in    (effective_adc)", text)

    def test_top_has_four_channel_safety(self):
        text = Path("rtl/waveform_control_4q_top.v").read_text()
        self.assertIn(
            "for (genvar ch = 0; ch < 4; ch++) begin : g_safety",
            text,
        )
        self.assertIn("assign safety_kill = |safety_kill_ch;", text)
        self.assertIn(
            "assign fault_flags = {12'b0, safety_fault_latched_ch};",
            text,
        )

    def test_prbs_datapath_sim_target_present(self):
        makefile = Path("Makefile").read_text()
        self.assertIn("sim-prbs:", makefile)
        self.assertIn("scripts/run_prbs_datapath_sim.py", makefile)

    def test_prbs_datapath_testbench_exists(self):
        self.assertTrue(Path("sim/tb_prbs_datapath.sv").exists())
        tb = Path("sim/tb_prbs_datapath.sv").read_text()
        self.assertIn("TB_PASS tb_prbs_datapath", tb)


if __name__ == "__main__":
    unittest.main()
