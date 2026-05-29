#!/usr/bin/env python3
"""Remove generated artifacts and transient build outputs."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GENERATED_ARTIFACTS = [
    "rtl/reciprocal_lut_w16_q24w25.mem",
    "reciprocal_lut_w16_q24w25.mem",
    "sim/gkp_cosim_vectors.hex",
    "register_map.json",
    "register_map.md",
    "register_map_issues.log",
    "cdc_crossing_suggestions.json",
    "cdc_crossing_suggestions.md",
    "reports/board_smoke_summary.json",
    "reports/board_smoke_summary.md",
    "reports/board_capture_prbs.hex",
    "reports/board_capture_packets.jsonl",
    "reports/board_read_build_id.json",
    "reports/board_axi_lite_smoke.json",
    "reports/board_config_apply_smoke.json",
    "reports/board_safety_trip_smoke.json",
    "reports/board_prbs_capture_smoke.json",
    "reports/board_axis_capture_smoke.json",
    "reports/board_telemetry_window_smoke.json",
    "reports/source_tree_clean.log",
    "reports/local_toolchain.log",
    "reports/rtl_sanity.log",
    "reports/rtl_arithmetic_audit.log",
    "reports/cdc_static.log",
    "reports/source_tree_hash.log",
    "reports/gkp_decoder_sim.log",
    "reports/q15_16_mult_sim_summary.json",
    "reports/q15_16_mult_sim_summary.md",
    "reports/q15_16_mult_sim.log",
    "reports/telemetry_counter_sim_summary.json",
    "reports/telemetry_counter_sim_summary.md",
    "reports/telemetry_counter_sim.log",
]

GENERATED_DIRS = [
    "sim/build",
    "build_dir",
    "__MACOSX",
    ".pytest_cache",
]

GLOB_PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/.DS_Store",
    "**/*.jou",
    "**/*.str",
    "**/*.wdb",
    "**/*.vcd",
    "**/*.fst",
    "dist/*.zip",
]


def clean_generated_artifacts(*, verbose: bool = False) -> list[Path]:
    removed: list[Path] = []

    for rel in GENERATED_DIRS:
        path = PROJECT_ROOT / rel
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            removed.append(path)
            if verbose:
                print(f"removed {path.relative_to(PROJECT_ROOT)}")

    for rel in GENERATED_ARTIFACTS:
        path = PROJECT_ROOT / rel
        if path.exists():
            path.unlink()
            removed.append(path)
            if verbose:
                print(f"removed {path.relative_to(PROJECT_ROOT)}")

    for pattern in GLOB_PATTERNS:
        for path in list(PROJECT_ROOT.glob(pattern)):
            if ".git" in path.parts:
                continue
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
            else:
                continue
            removed.append(path)
            if verbose:
                print(f"removed {path.relative_to(PROJECT_ROOT)}")

    return removed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove generated local-validation artifacts."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each removed file.",
    )
    args = parser.parse_args()

    removed = clean_generated_artifacts(verbose=args.verbose)
    print(f"removed_count={len(removed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
