import unittest
from pathlib import Path


class TestV20AtomicConfigAndDecoderHardening(unittest.TestCase):
    def test_regfile_has_shadow_and_apply_register(self):
        text = Path("rtl/axilite_regfile_full.v").read_text()
        self.assertIn("shd_prbs_enable", text)
        self.assertIn("shd_inv_delta_q", text)
        self.assertIn("8'h70", text)
        self.assertIn("cfg_update_pulse   <= 1'b1;", text)
        self.assertIn("reg_prbs_enable    <= shd_prbs_enable;", text)

    def test_register_header_exposes_cfg_apply(self):
        text = Path("firmware/registers.h").read_text()
        self.assertIn("WB_REG_CFG_APPLY", text)
        self.assertIn("WB_CFG_APPLY_COMMIT", text)

    def test_calibration_fsm_commits_alpha_updates(self):
        text = Path("firmware/calibration_fsm.c").read_text()
        self.assertIn("wb_commit_config", text)
        self.assertIn("wb_write(WB_REG_CFG_APPLY, WB_CFG_APPLY_COMMIT);", text)

    def test_decoder_stage2_uses_saturation_helper(self):
        text = Path("rtl/gkp_decoder.v").read_text()
        self.assertIn(
            "function automatic logic signed [ADC_WIDTH-1:0] sat_adc",
            text,
        )
        self.assertIn("lattice_idx_comb", text)
        self.assertIn("scaled_idx_full_comb > 64'sd32767", text)
        self.assertIn("remainder_int_comb", text)
        self.assertIn("remainder_s2 <= sat_adc(remainder_int_comb);", text)


if __name__ == "__main__":
    unittest.main()
