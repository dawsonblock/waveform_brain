import unittest
from pathlib import Path


class TestCompactPackage(unittest.TestCase):
    def test_heavy_generated_files_absent(self):
        self.assertFalse(Path("rtl/reciprocal_lut_w16_q24w25.mem").exists())
        self.assertFalse(Path("sim/gkp_cosim_vectors.hex").exists())
        self.assertFalse(Path("register_map.json").exists())

    def test_generators_present(self):
        self.assertTrue(Path("scripts/generate_reciprocal_lut.py").exists())
        self.assertTrue(Path("scripts/generate_gkp_cosim_vectors.py").exists())


if __name__ == "__main__":
    unittest.main()
