import unittest
from pathlib import Path


class TestV16PreboardOrdering(unittest.TestCase):
    def test_preboard_cleans_before_tests(self):
        text = Path("scripts/preboard_check.py").read_text()
        self.assertIn("clean_generated_artifacts()", text)
        clean_idx = text.find("clean_generated_artifacts()")
        test_idx = text.find('"unittest"')
        gen_idx = text.find("generate_reciprocal_lut.py")
        self.assertTrue(clean_idx < test_idx < gen_idx)

    def test_v16_doc_exists(self):
        self.assertTrue(Path("docs/PREBOARD_GATE_FIX_V16.md").exists())


if __name__ == "__main__":
    unittest.main()
