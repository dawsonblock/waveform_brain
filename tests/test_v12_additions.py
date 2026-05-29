import subprocess
import unittest
from pathlib import Path


class TestV12Additions(unittest.TestCase):
    def test_full_axi_files_exist(self):
        self.assertTrue(Path("rtl/axilite_regfile_full.v").exists())
        self.assertTrue(Path("rtl/waveform_brain_axi4lite_full_top.v").exists())

    def test_cosim_files_exist(self):
        self.assertTrue(Path("sim/tb_gkp_decoder_cosim.sv").exists())
        self.assertTrue(Path("scripts/generate_gkp_cosim_vectors.py").exists())
        self.assertTrue(Path("scripts/run_gkp_cosim.py").exists())

    def test_full_axi_has_ready_response_ports(self):
        text = Path("rtl/axilite_regfile_full.v").read_text()
        for token in ["s_axi_bready", "s_axi_rready", "s_axi_bresp", "s_axi_rresp"]:
            self.assertIn(token, text)

    def test_vector_generation(self):
        out = Path("sim/test_vectors_tmp.hex")
        if out.exists():
            out.unlink()
        proc = subprocess.run(
            ["python3", "scripts/generate_gkp_cosim_vectors.py", "--out", str(out), "--count", "8"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)
        lines = [ln for ln in out.read_text().splitlines() if ln and not ln.startswith("#")]
        self.assertEqual(len(lines), 8)
        out.unlink()


if __name__ == "__main__":
    unittest.main()
