import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class TestRtlSanityCheckBehavior(unittest.TestCase):
    def setUp(self):
        self.python = shutil.which("python3") or "python3"

    def run_check(self, rtl_dir: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self.python,
                "scripts/rtl_sanity_check.py",
                "--rtl-dir",
                str(rtl_dir),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )

    def test_fails_when_no_rtl_files_exist(self):
        with tempfile.TemporaryDirectory() as td:
            proc = self.run_check(Path(td))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("no RTL files found", proc.stdout)

    def test_fails_on_duplicate_assign(self):
        with tempfile.TemporaryDirectory() as td:
            rtl_dir = Path(td)
            (rtl_dir / "dup.v").write_text(
                textwrap.dedent("""\
                    module dup_assign;
                        logic a;
                        assign a = 1'b0;
                        assign a = 1'b1;
                    endmodule
                    """),
                encoding="utf-8",
            )
            proc = self.run_check(rtl_dir)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("duplicate continuous assign target", proc.stdout)


if __name__ == "__main__":
    unittest.main()
