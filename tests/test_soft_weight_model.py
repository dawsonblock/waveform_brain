import unittest

from userspace.soft_weight_model import (
    soft_weight_lut,
    soft_weight_div_reference,
    abs_signed16_as_u17,
)


class TestSoftWeightModel(unittest.TestCase):
    def test_abs_min_signed(self):
        self.assertEqual(abs_signed16_as_u17(0x8000), 32768)

    def test_zero_alpha(self):
        self.assertEqual(soft_weight_lut(0, 0), 0)

    def test_full_scale_when_denominator_equals_alpha(self):
        # alpha=1, r=0 should produce exactly 1.0 in Q8.8 = 256.
        self.assertEqual(soft_weight_lut(1, 0), 256)

    def test_lut_close_to_division_reference(self):
        cases = [
            (1, 0),
            (16, 0),
            (16, 1),
            (16, -1),
            (64, 10),
            (1024, -300),
            (65535, 0),
            (65535, -32768),
        ]
        for alpha, r in cases:
            lut = soft_weight_lut(alpha, r)
            div = soft_weight_div_reference(alpha, r)
            self.assertLessEqual(abs(lut - div), 1, (alpha, r, lut, div))


if __name__ == "__main__":
    unittest.main()
