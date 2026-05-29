import os
import shutil
import subprocess
import unittest


class TestAxiliteRegfileBehavior(unittest.TestCase):
    def test_axilite_behavioral_sim(self):
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            if os.environ.get("WB_STRICT_SIM") == "1":
                self.fail("iverilog/vvp required for strict simulation test")
            self.skipTest("iverilog/vvp missing")

        proc = subprocess.run(
            ["python3", "scripts/run_axilite_regfile_sim.py"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("TB_PASS tb_axilite_regfile_full", proc.stdout)


if __name__ == "__main__":
    unittest.main()
