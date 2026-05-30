#!/usr/bin/env python3
"""Build source or proof release archives for Waveform Brain."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"

SOURCE_DIRS = [
    ".github",
    ".trunk",
    "board_tests",
    "constraints",
    "docs",
    "firmware",
    "formal",
    "rtl",
    "scripts",
    "sim",
    "tests",
    "userspace",
]

SOURCE_FILES = [
    "Makefile",
    "README.md",
    ".gitignore",
]

SOURCE_EXCLUDES = {
    "__MACOSX",
    "sim/build",
    "build_dir",
    "reports",
    "sim/gkp_cosim_vectors.hex",
    "rtl/reciprocal_lut_w16_q24w25.mem",
    "reciprocal_lut_w16_q24w25.mem",
    "register_map.json",
    "register_map.md",
    "register_map_issues.log",
    "cdc_crossing_suggestions.json",
    "cdc_crossing_suggestions.md",
}

SOURCE_EXCLUDE_SUFFIXES = {
    ".pyc",
    ".jou",
    ".str",
    ".wdb",
    ".vcd",
    ".fst",
}

PROOF_LOCAL_REQUIRED = [
    "reports/preboard_local_summary.json",
    "reports/preboard_local_summary.md",
    "reports/local_toolchain_summary.json",
    "reports/source_tree_hash_summary.json",
    "reports/source_tree_hash.txt",
    "reports/source_tree_clean_summary.json",
    "reports/cdc_static_summary.json",
    "reports/register_map.json",
    "reports/unittest.log",
    "reports/make_validate.log",
    "reports/gkp_decoder_sim.log",
    "reports/axilite_regfile_sim_summary.json",
    "reports/axilite_regfile_sim.log",
    "reports/packer_axis_sim_summary.json",
    "reports/packer_axis_sim.log",
    "reports/safety_monitor_sim_summary.json",
    "reports/safety_monitor_sim.log",
    "reports/prbs_datapath_sim_summary.json",
    "reports/prbs_datapath_sim.log",
    "reports/cdc_cosim_summary.json",
    "reports/cdc_cosim.log",
    "reports/gkp_decoder_sim_summary.json",
    "reports/rtl_arithmetic_audit.json",
    "reports/rtl_arithmetic_audit.md",
    "reports/rtl_arithmetic_audit.log",
    "reports/rtl_sanity.log",
    "reports/release_prereq_summary_local.json",
    "reports/proof_manifest_local.json",
]

PROOF_BOARD_REQUIRED = [
    "reports/implementation_gate_summary.json",
    "reports/implementation_gate_summary.md",
    "reports/board_smoke_summary.json",
    "reports/board_capture_summary.json",
    "reports/cdc_critical_summary.json",
    "reports/cdc_cell_match_summary.md",
    "reports/timing_summary.rpt",
    "reports/drc.rpt",
    "reports/cdc_full.rpt",
    "reports/cdc_critical.rpt",
    "reports/clock_interaction.rpt",
    "reports/utilization.rpt",
    "reports/vivado_synth.log",
    "reports/vivado_impl.log",
    "reports/release_prereq_summary_board.json",
    "reports/proof_manifest_board.json",
]


def has_excluded_prefix(rel: Path) -> bool:
    rel_str = rel.as_posix()
    return any(
        rel_str == prefix or rel_str.startswith(f"{prefix}/")
        for prefix in SOURCE_EXCLUDES
    )


def collect_source_files() -> list[Path]:
    collected: list[Path] = []

    for rel_file in SOURCE_FILES:
        path = PROJECT_ROOT / rel_file
        if path.exists():
            collected.append(path)

    for rel_dir in SOURCE_DIRS:
        base = PROJECT_ROOT / rel_dir
        if not base.exists():
            continue
        for item in base.rglob("*"):
            if item.is_dir():
                continue
            rel_path = item.relative_to(PROJECT_ROOT)
            rel_str = rel_path.as_posix()
            if "/__pycache__/" in f"/{rel_str}/":
                continue
            if rel_str.endswith(".log") and not rel_str.startswith("reports/"):
                continue
            if any(rel_str.endswith(suf) for suf in SOURCE_EXCLUDE_SUFFIXES):
                continue
            if rel_str == ".DS_Store" or rel_str.endswith("/.DS_Store"):
                continue
            if has_excluded_prefix(rel_path):
                continue
            collected.append(item)

    return sorted(set(collected))


def collect_proof_files(*, mode: str) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    missing_required: list[str] = []
    required = list(PROOF_LOCAL_REQUIRED)
    if mode == "proof-board":
        required.extend(PROOF_BOARD_REQUIRED)

    for rel in required:
        path = PROJECT_ROOT / rel
        if path.exists():
            files.append(path)
        else:
            missing_required.append(rel)

    return sorted(set(files)), missing_required


def write_zip(files: list[Path], *, root_name: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            zf.write(path, f"{root_name}/{rel}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build source or proof release archive."
    )
    parser.add_argument(
        "--mode",
        choices=[
            "source",
            "proof",
            "proof-local",
            "proof-board",
            "board-impl",
            "board-capture",
        ],
        required=True,
        help="Archive type to build.",
    )
    parser.add_argument(
        "--name",
        default="waveform_brain-main",
        help="Root folder prefix inside archive.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output archive path. Defaults to dist/<name>-<mode>.zip",
    )
    args = parser.parse_args()

    mode = args.mode
    if mode == "proof":
        mode = "proof-local"
    if mode == "board-impl":
        mode = "proof-board"
    if mode == "board-capture":
        mode = "proof-board"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = args.out or DIST_DIR / f"{args.name}-{mode}-{stamp}.zip"
    root_name = f"{args.name}-{mode}"

    if mode == "source":
        files = collect_source_files()
        write_zip(files, root_name=root_name, out_path=out_path)
        print(f"mode=source files={len(files)} out={out_path}")
        return 0

    files, missing_required = collect_proof_files(mode=mode)
    if missing_required:
        print("missing required proof files:")
        for rel in missing_required:
            print(f"  {rel}")
        return 1

    write_zip(files, root_name=root_name, out_path=out_path)
    print(f"mode={mode} files={len(files)} out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
