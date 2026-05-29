import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def write_file(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def make_minimal_proof_local(base: Path) -> Path:
    root = base / "waveform_brain-main-proof-local"
    reports = root / "reports"

    common = {
        "schema_version": 1,
        "generated_at_utc": "2026-05-28T00:00:00Z",
        "command": "test",
        "source_tree_hash": "1" * 64,
        "pass": True,
    }

    required_json = [
        "preboard_local_summary.json",
        "local_toolchain_summary.json",
        "source_tree_hash_summary.json",
        "source_tree_clean_summary.json",
        "cdc_static_summary.json",
        "axilite_regfile_sim_summary.json",
        "packer_axis_sim_summary.json",
        "safety_monitor_sim_summary.json",
        "prbs_datapath_sim_summary.json",
        "gkp_decoder_sim_summary.json",
    ]
    for name in required_json:
        payload = dict(common)
        if name == "preboard_local_summary.json":
            payload["overall_pass"] = True
            payload["checks"] = []
        write_file(reports / name, json.dumps(payload))

    required_text = {
        "preboard_local_summary.md": "ok\n",
        "source_tree_hash.txt": "1" * 64 + "\n",
        "register_map.json": "{}\n",
        "unittest.log": "ok\n",
        "make_validate.log": "ok\n",
        "gkp_decoder_sim.log": "ok\n",
        "axilite_regfile_sim.log": "ok\n",
        "packer_axis_sim.log": "ok\n",
        "safety_monitor_sim.log": "ok\n",
        "prbs_datapath_sim.log": "ok\n",
        "rtl_arithmetic_audit.json": "{}\n",
        "rtl_arithmetic_audit.md": "ok\n",
        "rtl_arithmetic_audit.log": "ok\n",
        "rtl_sanity.log": "ok\n",
    }
    for name, data in required_text.items():
        write_file(reports / name, data)

    return root


def zip_tree(root: Path, out_zip: Path) -> None:
    with ZipFile(out_zip, "w", ZIP_DEFLATED) as zf:
        for item in sorted(root.rglob("*")):
            if item.is_dir():
                continue
            zf.write(item, item.relative_to(root.parent).as_posix())


class TestReleaseValidatorFailClosed(unittest.TestCase):
    def setUp(self) -> None:
        self.python = shutil.which("python3") or "python3"

    def run_validator(self, archive: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self.python,
                "scripts/validate_release_archive.py",
                str(archive),
                "--mode",
                "proof-local",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=90,
        )

    def test_fails_closed_when_required_file_missing(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = make_minimal_proof_local(td_path)
            (root / "reports" / "rtl_sanity.log").unlink()
            archive = td_path / "proof.zip"
            zip_tree(root, archive)

            proc = self.run_validator(archive)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(
                "missing required proof entry: reports/rtl_sanity.log",
                proc.stdout,
            )


if __name__ == "__main__":
    unittest.main()
