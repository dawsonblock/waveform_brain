import subprocess
import unittest
from pathlib import Path


class TestV18AxisCalibAudit(unittest.TestCase):
    def test_packer_holds_valid_until_ready(self):
        text = Path("rtl/packer_axis.v").read_text()
        self.assertIn("beat_accepted", text)
        self.assertIn("m_axis_tvalid <= 1'b1;", text)
        self.assertIn("Hold beat 0 stable until accepted", text)
        self.assertIn("Hold beat 1 stable until accepted", text)
        self.assertIn("pack_meta = {4'h2", text)
        self.assertNotIn("pack_meta = {4'h1", text)

    def test_registers_include_guard_contains_health_defs(self):
        text = Path("firmware/registers.h").read_text()
        endif = text.rfind("#endif")
        health = text.find("WB_REG_HEALTH_STATUS")
        self.assertTrue(health != -1 and health < endif)

    def test_calibration_fsm_has_alpha_tune(self):
        text = Path("firmware/calibration_fsm.c").read_text()
        self.assertIn("wb_tune_alpha_grid", text)
        self.assertIn("WB_REG_TELEM_FLIPS_DELTA", text)
        self.assertIn("settle_cycles", text)

    def test_arithmetic_audit_exists_and_runs(self):
        self.assertTrue(Path("scripts/audit_rtl_arithmetic.py").exists())
        proc = subprocess.run(
            ["python3", "scripts/audit_rtl_arithmetic.py"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_packet_parser_versioned_packet(self):
        from userspace.packet_parser import parse_packet
        data, syn, fault = parse_packet([0x0004000300020001, 0x1102000000000000])
        self.assertEqual(data, [1, 2, 3, 4])
        self.assertEqual(syn, [2, 0, 0, 0])
        self.assertTrue(fault)

    def test_v18_doc_exists(self):
        self.assertTrue(Path("docs/AXIS_CALIB_AUDIT_V18.md").exists())


if __name__ == "__main__":
    unittest.main()
