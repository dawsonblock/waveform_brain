import json
import tempfile
import unittest
from pathlib import Path

from scripts.parse_cdc_report import parse_cdc_report


class TestCDCReportParser(unittest.TestCase):
    def test_pass_clean_report(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "clean.rpt"
            p.write_text("CDC Summary\nNo issues here\n")
            self.assertEqual(parse_cdc_report(p), 0)

    def test_fail_unconstrained(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.rpt"
            p.write_text("Clock Domain Crossing Details\nNo user constraint found on this path\n")
            self.assertEqual(parse_cdc_report(p), 1)

    def test_json_and_markdown_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.rpt"
            j = Path(td) / "summary.json"
            m = Path(td) / "summary.md"
            p.write_text("Clock Domain Crossing Details\nUnknown CDC structure\n")
            rc = parse_cdc_report(p, json_out=j, md_out=m)
            self.assertEqual(rc, 1)
            data = json.loads(j.read_text())
            self.assertEqual(data["status"], "FAIL")
            self.assertIn("CDC Report Parser Summary", m.read_text())


if __name__ == "__main__":
    unittest.main()
