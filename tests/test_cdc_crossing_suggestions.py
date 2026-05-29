import unittest

from scripts.analyze_cdc_crossings import suggest_cdc_constraints


class TestCDCCrossingSuggestions(unittest.TestCase):
    def test_telemetry_payload_recommends_handshake(self):
        regs = [
            {
                "name": "TELEM_FLIPS_DELTA",
                "address": "0x40",
                "access": "R",
            },
            {
                "name": "TELEM_TOTAL_FLIPS",
                "address": "0x44",
                "access": "R",
            },
        ]

        suggestions = suggest_cdc_constraints(regs)
        self.assertEqual(len(suggestions), 2)
        for suggestion in suggestions:
            self.assertIn("xpm_cdc_handshake", suggestion["recommended"])
            self.assertNotIn("xpm_cdc_gray", suggestion["recommended"])


if __name__ == "__main__":
    unittest.main()
