import unittest
from userspace.golden_gkp_model import gkp_decode, gkp_decode_fixed_soft_lut


class TestGoldenGKPModel(unittest.TestCase):
    def test_identity(self):
        # If coeffs are zero and alpha=1,
        # decoder should return input when on lattice.
        m = 8192.0  # example ADC counts
        inv_delta = 1.0 / 4096.0
        delta_adc = 4096.0
        coeffs = [0.0, 0.0, 0.0, 0.0]
        alpha = 1.0
        corr = gkp_decode(m, inv_delta, delta_adc, coeffs, alpha)
        self.assertAlmostEqual(corr, m, delta=1e-6)

    def test_fixed_soft_lut_output_saturates_to_i16(self):
        inv_delta_q = 0x00010000
        delta_adc_q = 0x00010000
        coeffs_q = [0x00100000, 0x00008000, 0x00000000, 0x00000000]

        cases = [
            (0, 0x0010),
            (1234, 0x0040),
            (-1234, 0x0040),
            (32767, 0xFFFF),
            (-32768, 0xFFFF),
        ]
        for m, alpha in cases:
            out = gkp_decode_fixed_soft_lut(
                m, inv_delta_q, delta_adc_q, coeffs_q, alpha
            )
            self.assertIsInstance(out, int)
            self.assertGreaterEqual(out, -32768)
            self.assertLessEqual(out, 32767)


if __name__ == "__main__":
    unittest.main()
