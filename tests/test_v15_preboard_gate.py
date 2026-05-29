import subprocess
import tempfile
import unittest
from pathlib import Path
import json


class TestV15PreboardGate(unittest.TestCase):
    def test_new_scripts_exist(self):
        for rel in [
            "scripts/preboard_check.py",
            "scripts/implementation_gate.py",
            "scripts/package_vivado_signoff.py",
            "docs/PREBOARD_GATE_V15.md",
            "docs/BOARD_READY_TEMPLATE.md",
        ]:
            self.assertTrue(Path(rel).exists(), rel)

    def test_makefile_targets_exist(self):
        text = Path("Makefile").read_text()
        for target in ["preboard-check", "implementation-gate", "vivado-signoff-package"]:
            self.assertIn(target, text)

    def test_cdc_parser_json_output_on_clean_report(self):
        with tempfile.TemporaryDirectory() as td:
            report = Path(td) / "cdc.rpt"
            out = Path(td) / "summary.json"
            report.write_text("CDC Summary\nNo issues here\n")
            proc = subprocess.run(
                ["python3", "scripts/parse_cdc_report.py", str(report), "--json-out", str(out), "--fail-on-critical"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)
            data = json.loads(out.read_text())
            self.assertTrue(data["pass"])

    def test_cdc_parser_fails_on_critical(self):
        with tempfile.TemporaryDirectory() as td:
            report = Path(td) / "cdc.rpt"
            out = Path(td) / "summary.json"
            report.write_text("Critical Warning: Unknown CDC structure\n")
            proc = subprocess.run(
                ["python3", "scripts/parse_cdc_report.py", str(report), "--json-out", str(out), "--fail-on-critical"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0)
            data = json.loads(out.read_text())
            self.assertFalse(data["pass"])

    def test_implementation_gate_fails_when_reports_missing(self):
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "implementation_gate_summary.json"
            out_md = Path(td) / "implementation_gate_summary.md"
            proc = subprocess.run(
                [
                    "python3",
                    "scripts/implementation_gate.py",
                    "--reports",
                    td,
                    "--json-out",
                    str(out_json),
                    "--md-out",
                    str(out_md),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0)

    def test_implementation_gate_passes_with_required_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td)
            out_json = reports / "implementation_gate_summary.json"
            out_md = reports / "implementation_gate_summary.md"
            (reports / "cdc_critical_summary.json").write_text(
                json.dumps({"pass": True, "critical_total": 0}),
                encoding="utf-8",
            )
            (reports / "cdc_cell_match_summary.md").write_text(
                "| primitive | count |\n|---|---|\n| `xpm_cdc_single` | `1` |\n",
                encoding="utf-8",
            )
            (reports / "timing_summary.rpt").write_text(
                "\n".join(
                    [
                        "WNS(ns) 0.100",
                        "TNS(ns) 0.000",
                        "WHS(ns) 0.050",
                        "THS(ns) 0.000",
                        "WPWS(ns) 0.030",
                        "TPWS(ns) 0.000",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (reports / "drc.rpt").write_text("No errors\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    "python3",
                    "scripts/implementation_gate.py",
                    "--reports",
                    td,
                    "--json-out",
                    str(out_json),
                    "--md-out",
                    str(out_md),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_implementation_gate_fails_on_missing_timing_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td)
            out_json = reports / "implementation_gate_summary.json"
            out_md = reports / "implementation_gate_summary.md"
            (reports / "cdc_critical_summary.json").write_text(
                json.dumps({"pass": True, "critical_total": 0}),
                encoding="utf-8",
            )
            (reports / "cdc_cell_match_summary.md").write_text(
                "| primitive | count |\n|---|---|\n| `xpm_cdc_single` | `1` |\n",
                encoding="utf-8",
            )
            (reports / "timing_summary.rpt").write_text(
                "WNS(ns) 0.100\n",
                encoding="utf-8",
            )
            (reports / "drc.rpt").write_text("No errors\n", encoding="utf-8")

            proc = subprocess.run(
                [
                    "python3",
                    "scripts/implementation_gate.py",
                    "--reports",
                    td,
                    "--json-out",
                    str(out_json),
                    "--md-out",
                    str(out_md),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("missing timing metrics", proc.stdout)

    def test_implementation_gate_fails_on_drc_fail_classes(self):
        with tempfile.TemporaryDirectory() as td:
            reports = Path(td)
            out_json = reports / "implementation_gate_summary.json"
            out_md = reports / "implementation_gate_summary.md"
            (reports / "cdc_critical_summary.json").write_text(
                json.dumps({"pass": True, "critical_total": 0}),
                encoding="utf-8",
            )
            (reports / "cdc_cell_match_summary.md").write_text(
                "| primitive | count |\n|---|---|\n| `xpm_cdc_single` | `1` |\n",
                encoding="utf-8",
            )
            (reports / "timing_summary.rpt").write_text(
                "\n".join(
                    [
                        "WNS(ns) 0.100",
                        "TNS(ns) 0.000",
                        "WHS(ns) 0.050",
                        "THS(ns) 0.000",
                        "WPWS(ns) 0.030",
                        "TPWS(ns) 0.000",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (reports / "drc.rpt").write_text(
                "CRITICAL WARNING: [NSTD-1] Unspecified I/O standard\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python3",
                    "scripts/implementation_gate.py",
                    "--reports",
                    td,
                    "--json-out",
                    str(out_json),
                    "--md-out",
                    str(out_md),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("drc_fail_classes", proc.stdout)


if __name__ == "__main__":
    unittest.main()
