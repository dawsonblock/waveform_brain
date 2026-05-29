import unittest
from pathlib import Path


class TestV17FlowFixes(unittest.TestCase):
    def test_vivado_script_uses_script_relative_paths(self):
        text = Path("scripts/waveform_brain_bitstream.tcl").read_text()
        self.assertIn("info script", text)
        self.assertIn("project_root", text)
        self.assertIn("file join $project_root", text)

    def test_vivado_script_marks_systemverilog(self):
        text = Path("scripts/waveform_brain_bitstream.tcl").read_text()
        self.assertIn("file_type SystemVerilog", text)

    def test_vivado_script_gates_before_bitstream(self):
        text = Path("scripts/waveform_brain_bitstream.tcl").read_text()
        self.assertLess(
            text.find("implementation_gate.py"),
            text.find("write_bitstream"),
        )

    def test_cdc_xdc_has_no_broad_false_path(self):
        text = Path("constraints/cdc_xpm_wrapper_constraints.xdc").read_text()
        self.assertNotIn("set_false_path", text)
        self.assertNotIn("set_clock_groups -asynchronous", text)

    def test_makefile_validate_cleans_before_tests(self):
        text = Path("Makefile").read_text()
        self.assertIn(
            "validate: clean-generated check-source-clean "
            "test lint gen-lut extract-regs cdc-analyze",
            text,
        )
        self.assertRegex(
            text,
            r"^size-report:",
            msg="size-report target must be standalone",
        )


if __name__ == "__main__":
    unittest.main()
