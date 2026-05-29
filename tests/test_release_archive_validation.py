import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

LOCAL_MANIFEST_FILES = [
    "reports/preboard_local_summary.json",
    "reports/preboard_local_summary.md",
    "reports/local_toolchain_summary.json",
    "reports/source_tree_hash_summary.json",
    "reports/source_tree_hash.txt",
    "reports/source_tree_clean_summary.json",
    "reports/cdc_static_summary.json",
    "reports/register_map.json",
    "reports/unittest.log",
    "reports/make_validate.log",
    "reports/gkp_decoder_sim.log",
    "reports/axilite_regfile_sim_summary.json",
    "reports/axilite_regfile_sim.log",
    "reports/packer_axis_sim_summary.json",
    "reports/packer_axis_sim.log",
    "reports/safety_monitor_sim_summary.json",
    "reports/safety_monitor_sim.log",
    "reports/prbs_datapath_sim_summary.json",
    "reports/prbs_datapath_sim.log",
    "reports/gkp_decoder_sim_summary.json",
    "reports/rtl_arithmetic_audit.json",
    "reports/rtl_arithmetic_audit.md",
    "reports/rtl_arithmetic_audit.log",
    "reports/rtl_sanity.log",
    "reports/release_prereq_summary_local.json",
]

BOARD_MANIFEST_FILES = [
    "reports/implementation_gate_summary.json",
    "reports/implementation_gate_summary.md",
    "reports/board_smoke_summary.json",
    "reports/board_capture_summary.json",
    "reports/cdc_critical_summary.json",
    "reports/cdc_cell_match_summary.md",
    "reports/timing_summary.rpt",
    "reports/drc.rpt",
    "reports/cdc_full.rpt",
    "reports/cdc_critical.rpt",
    "reports/clock_interaction.rpt",
    "reports/utilization.rpt",
    "reports/vivado_synth.log",
    "reports/vivado_impl.log",
    "reports/release_prereq_summary_board.json",
]


PASS_SUMMARY_JSONS = {
    "reports/preboard_local_summary.json",
    "reports/local_toolchain_summary.json",
    "reports/source_tree_hash_summary.json",
    "reports/source_tree_clean_summary.json",
    "reports/cdc_static_summary.json",
    "reports/axilite_regfile_sim_summary.json",
    "reports/packer_axis_sim_summary.json",
    "reports/safety_monitor_sim_summary.json",
    "reports/prbs_datapath_sim_summary.json",
    "reports/gkp_decoder_sim_summary.json",
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    _write_text(path, json.dumps(payload))


def _make_manifest(
    root: Path,
    mode: str,
    paths: list[str],
    source_hash: str,
) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for rel in paths:
        path = root / rel
        entries.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    return {
        "schema_version": 1,
        "mode": mode,
        "generated_at_utc": "2026-05-28T00:00:00Z",
        "command": f"python3 scripts/generate_proof_manifest.py --mode {mode}",
        "pass": True,
        "source_tree_hash": source_hash,
        "required_file_count": len(entries),
        "files": entries,
    }


def build_proof_root(base: Path, *, include_board: bool = False) -> Path:
    root = base / "waveform_brain-main-proof"
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    source_hash = "abcd" * 16
    metadata = {
        "schema_version": 1,
        "generated_at_utc": "2026-05-28T00:00:00Z",
        "command": "python3 scripts/preboard_check.py --mode proof-local",
        "source_tree_hash": source_hash,
    }

    preboard = {
        **metadata,
        "pass": True,
        "overall_pass": True,
        "checks": [],
    }
    _write_json(reports / "preboard_local_summary.json", preboard)
    _write_text(reports / "preboard_local_summary.md", "ok\n")

    _write_json(
        reports / "local_toolchain_summary.json",
        {**metadata, "pass": True},
    )
    _write_json(
        reports / "source_tree_hash_summary.json",
        {
            **metadata,
            "pass": True,
            "command": "python3 scripts/hash_source_tree.py",
        },
    )
    _write_text(reports / "source_tree_hash.txt", f"{source_hash}\n")
    _write_json(
        reports / "source_tree_clean_summary.json",
        {
            **metadata,
            "pass": True,
            "command": "python3 scripts/check_source_tree_clean.py",
        },
    )
    _write_json(
        reports / "cdc_static_summary.json",
        {
            **metadata,
            "pass": True,
            "command": "python3 scripts/analyze_cdc_crossings.py",
        },
    )
    _write_json(reports / "register_map.json", {"registers": []})

    for summary in [
        "axilite_regfile",
        "packer_axis",
        "safety_monitor",
        "prbs_datapath",
        "gkp_decoder",
    ]:
        _write_json(
            reports / f"{summary}_sim_summary.json",
            {
                **metadata,
                "pass": True,
                "command": f"python3 scripts/run_{summary}_sim.py",
            },
        )
        _write_text(reports / f"{summary}_sim.log", f"{summary} sim ok\n")

    _write_json(reports / "rtl_arithmetic_audit.json", {"pass": True})
    _write_text(reports / "rtl_arithmetic_audit.md", "audit ok\n")
    _write_text(reports / "rtl_arithmetic_audit.log", "audit log\n")
    _write_text(reports / "rtl_sanity.log", "rtl sanity ok\n")
    _write_text(reports / "unittest.log", "tests ok\n")
    _write_text(reports / "make_validate.log", "validate ok\n")

    prereq_local = {
        "schema_version": 1,
        "mode": "proof-local",
        "generated_at_utc": metadata["generated_at_utc"],
        "command": (
            "python3 scripts/check_release_prereqs.py "
            "--mode proof-local"
        ),
        "pass": True,
        "checks": [{"name": "tools", "pass": True}],
    }
    _write_json(reports / "release_prereq_summary_local.json", prereq_local)

    local_manifest = _make_manifest(
        root,
        "proof-local",
        LOCAL_MANIFEST_FILES,
        source_hash,
    )
    _write_json(reports / "proof_manifest_local.json", local_manifest)

    if include_board:
        impl = {
            "generated_at_utc": metadata["generated_at_utc"],
            "pass": True,
            "checks": {
                "cdc_critical": {"pass": True, "detail": "ok"},
                "cdc_cell_match": {"pass": True, "detail": "ok"},
                "timing": {"pass": True, "detail": "ok"},
                "drc": {"pass": True, "detail": "ok"},
            },
        }
        _write_json(reports / "implementation_gate_summary.json", impl)
        _write_text(reports / "implementation_gate_summary.md", "ok\n")
        _write_json(reports / "board_smoke_summary.json", {"pass": True})
        _write_json(reports / "board_capture_summary.json", {"pass": True})
        _write_json(reports / "cdc_critical_summary.json", {"pass": True})
        _write_text(reports / "cdc_cell_match_summary.md", "ok\n")
        _write_text(reports / "timing_summary.rpt", "WNS(ns) 0.100\n")
        _write_text(reports / "drc.rpt", "No errors\n")
        _write_text(reports / "cdc_full.rpt", "No issues\n")
        _write_text(reports / "cdc_critical.rpt", "No issues\n")
        _write_text(reports / "clock_interaction.rpt", "No issues\n")
        _write_text(reports / "utilization.rpt", "No issues\n")
        _write_text(reports / "vivado_synth.log", "synth ok\n")
        _write_text(reports / "vivado_impl.log", "impl ok\n")

        prereq_board = {
            "schema_version": 1,
            "mode": "proof-board",
            "generated_at_utc": metadata["generated_at_utc"],
            "command": (
                "python3 scripts/check_release_prereqs.py "
                "--mode proof-board"
            ),
            "pass": True,
            "checks": [{"name": "tools", "pass": True}],
        }
        _write_json(
            reports / "release_prereq_summary_board.json",
            prereq_board,
        )

        board_manifest = _make_manifest(
            root,
            "proof-board",
            LOCAL_MANIFEST_FILES + BOARD_MANIFEST_FILES,
            source_hash,
        )
        _write_json(reports / "proof_manifest_board.json", board_manifest)

    return root


def zip_tree(root: Path, out_zip: Path) -> None:
    with ZipFile(out_zip, "w", ZIP_DEFLATED) as zf:
        for item in sorted(root.rglob("*")):
            if item.is_dir():
                continue
            zf.write(item, item.relative_to(root.parent).as_posix())


class TestReleaseArchiveValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.python = shutil.which("python3") or "python3"

    def run_validator(
        self,
        archive: Path,
        mode: str = "proof-local",
        *extra_args: str,
    ) -> subprocess.CompletedProcess[str]:
        cmd = [
            self.python,
            "scripts/validate_release_archive.py",
            str(archive),
            "--mode",
            mode,
            *extra_args,
        ]
        return subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=90,
        )

    def test_source_archive_rejects_partial_reports(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = td_path / "waveform_brain-main-source"
            _write_text(root / "Makefile", "x\n")
            _write_text(root / "README.md", "x\n")
            _write_text(
                root / "rtl" / "axilite_regfile_full.v",
                "module x; endmodule\n",
            )
            _write_text(root / "scripts" / "preboard_check.py", "")
            _write_text(root / "board_tests" / "run_board_smoke.py", "")
            _write_text(root / "board_tests" / "adapter_contract.py", "")
            _write_text(root / "tests" / "test_board_smoke_scaffold.py", "")
            _write_text(root / "tests" / "test_axilite_regfile_static.py", "")
            _write_text(root / "reports" / "proof_manifest_local.json", "{}")

            archive = td_path / "bad_source.zip"
            zip_tree(root, archive)
            proc = self.run_validator(archive, "source")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("forbidden source entry", proc.stdout)

    def test_proof_semantics_fail_when_preboard_failed(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = build_proof_root(td_path)

            preboard_path = root / "reports" / "preboard_local_summary.json"
            preboard = json.loads(preboard_path.read_text(encoding="utf-8"))
            preboard["pass"] = False
            preboard_path.write_text(json.dumps(preboard), encoding="utf-8")

            archive = td_path / "proof.zip"
            zip_tree(root, archive)
            proc = self.run_validator(archive, "proof-local")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("preboard_local_summary pass=false", proc.stdout)

    def test_proof_semantics_fail_when_impl_check_failed(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = build_proof_root(td_path, include_board=True)

            impl_path = root / "reports" / "implementation_gate_summary.json"
            impl = json.loads(impl_path.read_text(encoding="utf-8"))
            impl["checks"]["timing"]["pass"] = False
            impl_path.write_text(json.dumps(impl), encoding="utf-8")

            board_manifest_path = (
                root / "reports" / "proof_manifest_board.json"
            )
            board_manifest = _make_manifest(
                root,
                "proof-board",
                LOCAL_MANIFEST_FILES + BOARD_MANIFEST_FILES,
                "abcd" * 16,
            )
            board_manifest_path.write_text(
                json.dumps(board_manifest),
                encoding="utf-8",
            )

            archive = td_path / "proof.zip"
            zip_tree(root, archive)
            proc = self.run_validator(archive, "proof-board")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("implementation check failed: timing", proc.stdout)

    def test_board_proof_requires_raw_logs(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = build_proof_root(td_path, include_board=True)
            (root / "reports" / "gkp_decoder_sim.log").unlink()
            archive = td_path / "proof.zip"
            zip_tree(root, archive)

            proc = self.run_validator(archive, "proof-board")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("missing required proof entry", proc.stdout)
            self.assertIn("reports/gkp_decoder_sim.log", proc.stdout)

    def test_proof_semantics_fail_when_metadata_missing(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = build_proof_root(td_path)
            p = root / "reports" / "packer_axis_sim_summary.json"
            data = json.loads(p.read_text(encoding="utf-8"))
            data.pop("generated_at_utc", None)
            p.write_text(json.dumps(data), encoding="utf-8")

            archive = td_path / "proof.zip"
            zip_tree(root, archive)
            proc = self.run_validator(archive, "proof-local")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(
                "missing metadata field generated_at_utc",
                proc.stdout,
            )

    def test_proof_semantics_fail_when_hash_text_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = build_proof_root(td_path)
            (root / "reports" / "source_tree_hash.txt").write_text(
                "f" * 64 + "\n",
                encoding="utf-8",
            )

            archive = td_path / "proof.zip"
            zip_tree(root, archive)
            proc = self.run_validator(archive, "proof-local")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(
                "proof freshness failure",
                proc.stdout,
            )

    def test_proof_semantics_fail_when_summary_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = build_proof_root(td_path)
            p = root / "reports" / "packer_axis_sim_summary.json"
            data = json.loads(p.read_text(encoding="utf-8"))
            data["source_tree_hash"] = "0" * 64
            p.write_text(json.dumps(data), encoding="utf-8")

            archive = td_path / "proof.zip"
            zip_tree(root, archive)
            proc = self.run_validator(archive, "proof-local")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("hash mismatch", proc.stdout)

    def test_manifest_semantics_fail_when_listed_file_missing(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = build_proof_root(td_path)
            manifest_path = root / "reports" / "proof_manifest_local.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["files"].append(
                {
                    "path": "reports/does_not_exist.log",
                    "size": 1,
                    "sha256": "a" * 64,
                }
            )
            payload["required_file_count"] = len(payload["files"])
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            archive = td_path / "proof.zip"
            zip_tree(root, archive)
            proc = self.run_validator(archive, "proof-local")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(
                "lists missing file reports/does_not_exist.log",
                proc.stdout,
            )

    def test_manifest_semantics_fail_when_listed_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = build_proof_root(td_path)
            manifest_path = root / "reports" / "proof_manifest_local.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["files"][0]["sha256"] = "b" * 64
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            archive = td_path / "proof.zip"
            zip_tree(root, archive)
            proc = self.run_validator(archive, "proof-local")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("hash mismatch", proc.stdout)

    def test_manifest_semantics_fail_on_extra_unlisted_archive_file(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            root = build_proof_root(td_path)
            _write_text(root / "reports" / "unexpected_extra.log", "noise\n")

            archive = td_path / "proof.zip"
            zip_tree(root, archive)
            proc = self.run_validator(archive, "proof-local")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("does not list archive file", proc.stdout)


if __name__ == "__main__":
    unittest.main()
