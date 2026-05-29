import unittest
from pathlib import Path


class TestV23RepairBaseline(unittest.TestCase):
    def test_status_word_assignment_is_exactly_16_bits(self):
        text = Path("rtl/waveform_control_4q_top.v").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "assign status_word = {safety_kill, dec_valid_out, 11'h0};",
            text,
        )
        self.assertNotIn(
            "assign status_word = {safety_kill, dec_valid_out, 12'h0};",
            text,
        )

    def test_board_checklist_prbs_address_matches_register_map(self):
        checklist = Path("docs/BOARD_VERIFICATION_CHECKLIST.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Enable PRBS test mode (register `0x0C`).", checklist)
        self.assertNotIn("Enable PRBS test mode (register `0x60`).", checklist)

        reg_header = Path("firmware/registers.h").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            reg_header,
            r"#define\s+WB_REG_PRBS_ENABLE\s+0x0C\b",
        )
        self.assertNotRegex(
            reg_header,
            r"#define\s+WB_REG_PRBS_ENABLE\s+0x60\b",
        )

    def test_preboard_check_requests_hash_text_output(self):
        text = Path("scripts/preboard_check.py").read_text(encoding="utf-8")
        self.assertIn('"scripts/hash_source_tree.py"', text)
        self.assertIn('"--out-txt"', text)
        self.assertIn('"reports/source_tree_hash.txt"', text)


if __name__ == "__main__":
    unittest.main()
