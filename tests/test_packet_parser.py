import unittest
from userspace.packet_parser import parse_packet


class TestPacketParser(unittest.TestCase):
    def test_parse(self):
        """Test parsing of a two‑beat packet."""
        # Compose a test packet: fault=1, syn3=2, data3=0x1234,
        # syn2=1, data2=0xABCD, syn1=0, data1=0x0F0F, syn0=3, data0=0x5555
        # First beat: contains the four data words (little‑endian within the 64 bits)
        data_word = (
            (0x1234 << 48) |
            (0xABCD << 32) |
            (0x0F0F << 16) |
            (0x5555)
        )
        # Second beat: metadata in upper 16 bits: [15:9]=0, bit8=fault, bits7:6=syn3,
        # bits5:4=syn2, bits3:2=syn1, bits1:0=syn0.
        meta = (
            (1 << 8) |   # fault = 1
            (2 << 6) |   # syn3 = 2
            (1 << 4) |   # syn2 = 1
            (0 << 2) |   # syn1 = 0
            (3 << 0)     # syn0 = 3
        )
        meta_word = (meta << 48)  # place meta in bits[63:48]
        # Parse using the updated parser
        data, syn, fault = parse_packet([data_word, meta_word])
        self.assertEqual(fault, True)
        self.assertEqual(data, [0x5555, 0x0F0F, 0xABCD, 0x1234])
        self.assertEqual(syn, [3, 0, 1, 2])


if __name__ == '__main__':
    unittest.main()