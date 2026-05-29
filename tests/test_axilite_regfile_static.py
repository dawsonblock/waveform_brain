import unittest
from pathlib import Path


class TestAxiLiteRegfileStatic(unittest.TestCase):
    def setUp(self):
        self.text = Path("rtl/axilite_regfile.v").read_text()

    def test_no_old_always_ready_comb(self):
        self.assertNotIn("awready  = 1'b1", self.text)
        self.assertNotIn("wready   = 1'b1", self.text)
        self.assertNotIn("arready  = 1'b1", self.text)

    def test_has_write_and_read_accept_logic(self):
        self.assertIn("wire write_accept", self.text)
        self.assertIn("wire read_accept", self.text)
        self.assertIn("write_busy", self.text)
        self.assertIn("read_busy", self.text)

    def test_command_outputs_are_pulses(self):
        self.assertIn("clear_faults_pulse", self.text)
        self.assertIn("telem_start_pulse", self.text)
        self.assertIn("telem_clear_pulse", self.text)

    def test_wstrb_helper_exists(self):
        self.assertIn("function automatic [31:0] apply_wstrb", self.text)


if __name__ == "__main__":
    unittest.main()
