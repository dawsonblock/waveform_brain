import os
import shutil
import subprocess
import unittest


class TestPackerAxisBehavior(unittest.TestCase):
    def test_packer_stall_behavioral_sim(self):
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            if os.environ.get("WB_STRICT_SIM") == "1":
                self.fail("iverilog/vvp required for strict simulation test")
            self.skipTest("iverilog/vvp missing")

        proc = subprocess.run(
            ["python3", "scripts/run_packer_axis_sim.py"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("TB_PASS tb_packer_axis_stall", proc.stdout)


if __name__ == "__main__":
    unittest.main()
