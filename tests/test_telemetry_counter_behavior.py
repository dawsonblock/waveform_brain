import os
import shutil
import subprocess
import unittest


class TestTelemetryCounterBehavior(unittest.TestCase):
    def test_telemetry_counter_window_close_sim(self):
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            if os.environ.get("WB_STRICT_SIM") == "1":
                self.fail("iverilog/vvp required for strict simulation test")
            self.skipTest("iverilog/vvp missing")

        proc = subprocess.run(
            ["python3", "scripts/run_telemetry_counter_sim.py"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("TB_PASS tb_telemetry_counter_window", proc.stdout)


if __name__ == "__main__":
    unittest.main()
