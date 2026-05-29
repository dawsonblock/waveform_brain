import unittest
from pathlib import Path


class TestCDCv14Static(unittest.TestCase):
    def test_cdc_wrapper_exists_and_uses_xpm(self):
        text = Path("rtl/waveform_brain_cdc_wrapper.v").read_text()
        for token in [
            "xpm_cdc_handshake",
            "xpm_cdc_pulse",
            "xpm_cdc_single",
            "xpm_cdc_array_single",
            "xpm_cdc_gray",
        ]:
            self.assertIn(token, text)

    def test_telemetry_payload_uses_handshake_not_gray(self):
        text = Path("rtl/waveform_brain_cdc_wrapper.v").read_text()
        self.assertIn("u_telem_payload_hs", text)
        self.assertIn(".src_send (fab_telem_sample_done)", text)
        self.assertIn(".dest_req (axi_telem_sample_done)", text)
        self.assertNotIn("u_telem_flips_delta_gray", text)
        self.assertNotIn("u_telem_total_flips_gray", text)

    def test_cdc_top_exists(self):
        text = Path("rtl/waveform_brain_axi4lite_cdc_top.v").read_text()
        self.assertIn("fabric_clk", text)
        self.assertIn("s_axi_aclk", text)
        self.assertIn("waveform_brain_cdc_wrapper", text)

    def test_regfile_has_cfg_update_pulse(self):
        text = Path("rtl/axilite_regfile_full.v").read_text()
        self.assertIn("cfg_update_pulse", text)
        self.assertRegex(text, r"cfg_update_pulse\s*<=\s*1'b1")
        self.assertIn("8'h70", text)
        self.assertIn("reg_prbs_enable    <= shd_prbs_enable;", text)

    def test_cdc_constraints_and_signoff_docs_exist(self):
        self.assertTrue(
            Path("constraints/cdc_xpm_wrapper_constraints.xdc").exists()
        )
        self.assertTrue(Path("docs/CDC_HARDENING_V14.md").exists())
        self.assertTrue(Path("docs/PHASE1_SIGNOFF_SHEET.md").exists())
        self.assertTrue(Path("scripts/package_cdc_signoff.py").exists())

    def test_bitstream_defaults_to_cdc_top(self):
        text = Path("scripts/waveform_brain_bitstream.tcl").read_text()
        self.assertIn("waveform_brain_axi4lite_cdc_top", text)
        self.assertIn("CDC_VERIFY_FAIL_ON_ZERO 1", text)


if __name__ == "__main__":
    unittest.main()
