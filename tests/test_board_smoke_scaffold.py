import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestBoardSmokeScaffold(unittest.TestCase):
    def setUp(self) -> None:
        self.python = shutil.which("python3") or "python3"

    def test_board_smoke_is_fail_closed_with_reason_codes(self):
        with tempfile.TemporaryDirectory() as td:
            reports_dir = Path(td) / "reports"
            cmd = [
                self.python,
                "board_tests/run_board_smoke.py",
                "--device",
                "dummy",
                "--reports-dir",
                str(reports_dir),
            ]
            proc = subprocess.run(
                cmd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=90,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout)

            smoke_path = reports_dir / "board_smoke_summary.json"
            capture_path = reports_dir / "board_capture_summary.json"
            self.assertTrue(smoke_path.exists())
            self.assertTrue(capture_path.exists())

            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            capture = json.loads(capture_path.read_text(encoding="utf-8"))

            self.assertFalse(smoke["pass"])
            self.assertEqual(smoke["status"], "blocked")
            self.assertTrue(smoke["fail_closed"])
            self.assertIn("adapter_contract_version", smoke)

            for item in smoke["checks"]:
                self.assertEqual(item["status"], "blocked")
                self.assertFalse(item["pass"])
                self.assertTrue(item["fail_closed"])
                self.assertIn("reason_code", item)
                self.assertTrue(
                    str(item["reason_code"]).endswith(
                        "NOT_IMPLEMENTED"
                    )
                )

            self.assertFalse(capture["pass"])
            self.assertEqual(capture["status"], "blocked")
            self.assertTrue(capture["fail_closed"])
            self.assertEqual(
                capture["reason_code"],
                "BOARD_CAPTURE_ADAPTER_NOT_IMPLEMENTED",
            )


if __name__ == "__main__":
    unittest.main()
