import shutil
import subprocess
import tempfile
import unittest
import os
from pathlib import Path
from zipfile import ZipFile


class TestSourceArchiveSelfTest(unittest.TestCase):
    def setUp(self) -> None:
        self.python = shutil.which("python3") or "python3"

    def test_source_archive_contains_board_scaffold_and_runs_subset(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            archive = td_path / "source.zip"

            build_cmd = [
                self.python,
                "scripts/build_release_archive.py",
                "--mode",
                "source",
                "--out",
                str(archive),
            ]
            build_proc = subprocess.run(
                build_cmd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
            )
            self.assertEqual(build_proc.returncode, 0, build_proc.stdout)

            validate_cmd = [
                self.python,
                "scripts/validate_release_archive.py",
                str(archive),
                "--mode",
                "source",
            ]
            validate_proc = subprocess.run(
                validate_cmd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
            )
            self.assertEqual(validate_proc.returncode, 0, validate_proc.stdout)

            with ZipFile(archive) as zf:
                report_entries = [
                    name
                    for name in zf.namelist()
                    if "/reports/" in name and not name.endswith("/")
                ]
                self.assertEqual(report_entries, [])
                roots = {
                    Path(name).parts[0]
                    for name in zf.namelist()
                    if name and not name.endswith("/")
                }
                self.assertEqual(len(roots), 1)
                root = next(iter(roots))
                zf.extractall(td_path / "extract")

            extracted_root = td_path / "extract" / root
            self.assertTrue(
                (
                    extracted_root
                    / "board_tests"
                    / "run_board_smoke.py"
                ).exists()
            )
            self.assertTrue(
                (
                    extracted_root
                    / "board_tests"
                    / "adapter_contract.py"
                ).exists()
            )

            test_cmd = [
                self.python,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_board_smoke_scaffold.py",
            ]
            test_proc = subprocess.run(
                test_cmd,
                cwd=extracted_root,
                env={**os.environ, "PYTHONPATH": "."},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=180,
            )
            self.assertEqual(test_proc.returncode, 0, test_proc.stdout)


if __name__ == "__main__":
    unittest.main()
