import unittest

from userspace.config_staged_apply import (
    WB_CFG_APPLY_COMMIT,
    WB_REG_ALPHA,
    WB_REG_CFG_APPLY,
    WB_REG_COEFF0,
    WB_REG_INV_DELTA_Q,
    apply_staged_config,
)


class TestConfigStagedApply(unittest.TestCase):
    def test_stages_fields_then_commits_once(self):
        writes = []

        def mock_write(offset, value):
            writes.append((offset, value))

        apply_staged_config(
            mock_write,
            inv_delta_q=0x00010000,
            coeff0=0x00008000,
            alpha=0x20,
            commit=True,
        )

        self.assertEqual(
            writes,
            [
                (WB_REG_INV_DELTA_Q, 0x00010000),
                (WB_REG_COEFF0, 0x00008000),
                (WB_REG_ALPHA, 0x20),
                (WB_REG_CFG_APPLY, WB_CFG_APPLY_COMMIT),
            ],
        )

    def test_can_stage_without_commit(self):
        writes = []

        def mock_write(offset, value):
            writes.append((offset, value))

        apply_staged_config(mock_write, alpha=0x40, commit=False)
        self.assertEqual(writes, [(WB_REG_ALPHA, 0x40)])


if __name__ == "__main__":
    unittest.main()
