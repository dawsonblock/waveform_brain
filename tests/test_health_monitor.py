import tempfile
import unittest
from pathlib import Path

from userspace.health_monitor import parse_register_dump, snapshot_from_regs, REG_HEALTH_STATUS


class TestHealthMonitorHelper(unittest.TestCase):
    def test_parse_named_dump(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "dump.txt"
            path.write_text(
                "\n".join(
                    [
                        "HEALTH_STATUS=0x00000007",
                        "HEALTH_SAFETY_TRIPS=0x00000002",
                        "HEALTH_AXIS_STALLS=0x00000003",
                        "HEALTH_DEC_VALID=0x00000004",
                        "HEALTH_TELEM_DONE=0x00000005",
                    ]
                )
            )
            regs = parse_register_dump(str(path))
            snap = snapshot_from_regs(regs)
            self.assertEqual(regs[REG_HEALTH_STATUS], 7)
            self.assertTrue(snap.safety_fault_latched)
            self.assertTrue(snap.safety_kill)
            self.assertTrue(snap.axis_backpressure_now)
            self.assertEqual(snap.safety_trips, 2)
            self.assertEqual(snap.axis_stalls, 3)
            self.assertEqual(snap.decoder_valid_cycles, 4)
            self.assertEqual(snap.telemetry_done_windows, 5)


if __name__ == "__main__":
    unittest.main()
