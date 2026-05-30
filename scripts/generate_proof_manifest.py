#!/usr/bin/env python3
"""Generate compact proof manifest with file digests and canonical hash."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_LOCAL = [
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
]

REQUIRED_BOARD = [
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
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_canonical_hash() -> str:
    summary_path = PROJECT_ROOT / "reports/source_tree_hash_summary.json"
    txt_path = PROJECT_ROOT / "reports/source_tree_hash.txt"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise RuntimeError(
            "source_tree_hash_summary.json must be a JSON object"
        )

    value = summary.get("source_tree_hash")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            "source_tree_hash_summary.json missing source_tree_hash"
        )
    canonical = value.strip()

    text_hash = txt_path.read_text(encoding="utf-8").strip()
    if text_hash != canonical:
        raise RuntimeError(
            "reports/source_tree_hash.txt does not match canonical summary"
        )

    return canonical


def required_for_mode(mode: str) -> list[str]:
    required = list(REQUIRED_LOCAL)
    if mode == "proof-board":
        required.extend(REQUIRED_BOARD)
    return required


def default_output(mode: str) -> Path:
    if mode == "proof-board":
        return PROJECT_ROOT / "reports/proof_manifest_board.json"
    return PROJECT_ROOT / "reports/proof_manifest_local.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate proof manifest")
    parser.add_argument(
        "--mode",
        choices=["proof-local", "proof-board"],
        default="proof-local",
        help="Manifest strictness mode",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output path for manifest JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mode = args.mode
    output = Path(args.out) if args.out else default_output(mode)

    required = required_for_mode(mode)
    missing = []
    entries = []

    for rel in required:
        path = PROJECT_ROOT / rel
        if not path.exists():
            missing.append(rel)
            continue
        entries.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    if missing:
        print("proof-manifest-fail: missing required files")
        for rel in missing:
            print(f"  {rel}")
        return 1

    canonical_hash = read_canonical_hash()
    payload = {
        "schema_version": 1,
        "mode": mode,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": (
            "python3 scripts/generate_proof_manifest.py "
            f"--mode {mode}"
        ),
        "pass": True,
        "source_tree_hash": canonical_hash,
        "required_file_count": len(entries),
        "files": entries,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"proof-manifest-pass mode={mode} out={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
