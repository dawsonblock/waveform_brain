import os
import shutil
import subprocess
import unittest
from pathlib import Path


class TestGkpDecoderEdgeCosim(unittest.TestCase):
    @staticmethod
    def _cleanup_generated_rom_files():
        for rel in [
            "rtl/reciprocal_lut_w16_q24w25.mem",
            "reciprocal_lut_w16_q24w25.mem",
        ]:
            p = Path(rel)
            if p.exists():
                p.unlink()

    def test_edge_vector_generation_profile(self):
        out = Path("sim/gkp_cosim_vectors_edge_tmp.hex")
        if out.exists():
            out.unlink()

        proc = subprocess.run(
            [
                "python3",
                "scripts/generate_gkp_cosim_vectors.py",
                "--out",
                str(out),
                "--count",
                "16",
                "--profile",
                "edge",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)
        lines = [
            ln
            for ln in out.read_text().splitlines()
            if ln and not ln.startswith("#")
        ]
        self.assertEqual(len(lines), 16)
        self.assertTrue(any(ln.startswith("8000") for ln in lines))
        out.unlink()

    def test_edge_cosim_optional(self):
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            if os.environ.get("WB_STRICT_SIM") == "1":
                self.fail("iverilog/vvp required for strict simulation test")
            self.skipTest("iverilog/vvp missing")

        out = Path("sim/gkp_cosim_vectors_edge_tmp.hex")
        try:
            gen = subprocess.run(
                [
                    "python3",
                    "scripts/generate_gkp_cosim_vectors.py",
                    "--out",
                    str(out),
                    "--count",
                    "24",
                    "--profile",
                    "edge",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertEqual(gen.returncode, 0, gen.stdout)

            proc = subprocess.run(
                [
                    "python3",
                    "scripts/run_gkp_cosim.py",
                    "--vectors",
                    str(out),
                    "--use-existing-vectors",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)
        finally:
            if out.exists():
                out.unlink()
            self._cleanup_generated_rom_files()


if __name__ == "__main__":
    unittest.main()
