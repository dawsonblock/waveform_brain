import subprocess
import tempfile
import unittest
from pathlib import Path


class TestV19StreamingRobustness(unittest.TestCase):
    def test_new_axis_modules_exist(self):
        self.assertTrue(Path("rtl/axis_packet_fifo.v").exists())
        self.assertTrue(Path("rtl/axis_skid_buffer.v").exists())

    def test_fifo_drives_known_value_when_empty(self):
        text = Path("rtl/axis_packet_fifo.v").read_text()
        self.assertIn(
            "assign {m_axis_tlast, m_axis_tdata} = empty ? '0 : mem[rd_ptr];",
            text,
        )

    def test_packer_has_sequence_and_drop_counter(self):
        text = Path("rtl/packer_axis.v").read_text()
        self.assertIn("sequence_counter", text)
        self.assertIn("frame_drop_count", text)
        self.assertIn("4'h2", text)
        self.assertIn("Hold beat 0 stable until accepted", text)

    def test_top_inserts_fifo_after_packer(self):
        text = Path("rtl/waveform_control_4q_top.v").read_text()
        self.assertIn("axis_packet_fifo", text)
        self.assertIn("packer_tdata", text)
        self.assertIn("axis_fifo_overflow_count", text)
        self.assertLess(
            text.find("packer_axis"),
            text.find("axis_packet_fifo"),
        )

    def test_regfile_exposes_streaming_diagnostics(self):
        text = Path("rtl/axilite_regfile_full.v").read_text()
        for addr in ["8'h5C", "8'h60", "8'h64", "8'h68", "8'h6C"]:
            self.assertIn(addr, text)
        self.assertIn("axis_sequence_count_in", text)

    def test_cdc_wrapper_syncs_streaming_diagnostics(self):
        text = Path("rtl/waveform_brain_cdc_wrapper.v").read_text()
        for token in [
            "u_axis_fifo_level_array",
            "u_axis_fifo_overflow_gray",
            "u_axis_fifo_stall_gray",
            "u_axis_frame_drop_gray",
            "u_axis_sequence_gray",
        ]:
            self.assertIn(token, text)

    def test_packet_parser_v2_sequence(self):
        from userspace.packet_parser import (
            parse_packet_record,
            validate_monotonic_sequences,
        )
        rec0 = parse_packet_record([0x0004000300020001, 0x2102000000000007])
        rec1 = parse_packet_record([0x0008000700060005, 0x2000000000000008])
        self.assertEqual(rec0.version, 2)
        self.assertEqual(rec0.sequence, 7)
        self.assertEqual(rec0.syndromes, [2, 0, 0, 0])
        self.assertTrue(rec0.fault)
        self.assertEqual(validate_monotonic_sequences([rec0, rec1]), [])

    def test_capture_validator_detects_sequence_gap(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "capture.txt"
            path.write_text(
                "0004000300020001\n2102000000000007\n"
                "0008000700060005\n2000000000000009\n"
            )
            proc = subprocess.run(
                ["python3", "userspace/validate_packet_capture.py", str(path)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("sequence", proc.stdout)

    def test_formal_properties_exist(self):
        self.assertTrue(Path("formal/packer_axis_properties.sv").exists())

    def test_v19_doc_exists(self):
        path = Path("docs/STREAMING_ROBUSTNESS_V19.md")
        self.assertTrue(path.exists())
        text = path.read_text()
        self.assertIn("busy-valid-cycle counter", text)


if __name__ == "__main__":
    unittest.main()
