#!/usr/bin/env python3
"""Validate source/proof release archives for safety and required content."""

from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath
from zipfile import ZipFile

REQUIRED_SOURCE = [
    "Makefile",
    "README.md",
    "rtl/axilite_regfile_full.v",
    "scripts/preboard_check.py",
    "tests/test_axilite_regfile_static.py",
]

FORBIDDEN_SOURCE_PREFIXES = [
    "__MACOSX/",
    "sim/build/",
    "build_dir/",
]

FORBIDDEN_SOURCE_SUFFIXES = [
    ".pyc",
    ".jou",
    ".str",
    ".wdb",
    ".vcd",
    ".fst",
]

FORBIDDEN_SOURCE_EXACT = [
    ".DS_Store",
    "rtl/reciprocal_lut_w16_q24w25.mem",
    "reciprocal_lut_w16_q24w25.mem",
    "register_map.json",
    "register_map.md",
    "register_map_issues.log",
    "cdc_crossing_suggestions.json",
    "cdc_crossing_suggestions.md",
    "sim/gkp_cosim_vectors.hex",
]

REQUIRED_PROOF_LOCAL = [
    "reports/preboard_local_summary.json",
    "reports/preboard_local_summary.md",
    "reports/unittest.log",
    "reports/make_validate.log",
    "reports/cosim_gkp.log",
    "reports/axilite_regfile_sim_summary.json",
    "reports/axilite_regfile_sim.log",
    "reports/packer_axis_sim_summary.json",
    "reports/packer_axis_sim.log",
    "reports/safety_monitor_sim_summary.json",
    "reports/safety_monitor_sim.log",
    "reports/rtl_arithmetic_audit.json",
    "reports/rtl_arithmetic_audit.md",
]

REQUIRED_PROOF_BOARD = [
    "reports/implementation_gate_summary.json",
    "reports/implementation_gate_summary.md",
    "reports/cdc_critical_summary.json",
    "reports/cdc_cell_match_summary.md",
    "reports/timing_summary.rpt",
    "reports/drc.rpt",
    "reports/cdc_full.rpt",
    "reports/cdc_critical.rpt",
    "reports/clock_interaction.rpt",
    "reports/utilization.rpt",
    "reports/cosim_gkp.log",
    "reports/unittest.log",
    "reports/make_validate.log",
    "reports/vivado_synth.log",
    "reports/vivado_impl.log",
]

REQUIRED_IMPL_CHECKS = [
    "cdc_critical",
    "cdc_cell_match",
    "timing",
    "drc",
]


def unsafe_entry(name: str) -> bool:
    path = PurePosixPath(name)
    if path.is_absolute():
        return True
    return any(part == ".." for part in path.parts)


def single_root(entries: list[str]) -> tuple[bool, str]:
    roots = {
        PurePosixPath(entry).parts[0]
        for entry in entries
        if PurePosixPath(entry).parts
    }
    if len(roots) != 1:
        return False, ",".join(sorted(roots))
    return True, next(iter(roots))


def strip_root(entry: str) -> str:
    parts = PurePosixPath(entry).parts
    if len(parts) <= 1:
        return ""
    return PurePosixPath(*parts[1:]).as_posix()


def parse_required_json(
    *,
    zf: ZipFile,
    rel_to_name: dict[str, str],
    rel: str,
) -> tuple[dict[str, object] | None, str | None]:
    name = rel_to_name.get(rel)
    if name is None:
        return None, f"missing required proof entry: {rel}"
    try:
        payload = zf.read(name)
    except KeyError:
        return None, f"missing required proof entry: {rel}"
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None, f"malformed JSON proof entry: {rel}"
    if not isinstance(data, dict):
        return None, f"invalid JSON object in proof entry: {rel}"
    return data, None


def validate_preboard_semantics(
    *,
    zf: ZipFile,
    rel_to_name: dict[str, str],
) -> str | None:
    preboard, err = parse_required_json(
        zf=zf,
        rel_to_name=rel_to_name,
        rel="reports/preboard_local_summary.json",
    )
    if err is not None:
        return err
    assert preboard is not None
    if not bool(preboard.get("pass", False)):
        return "proof semantic failure: preboard_local_summary pass=false"

    return None


def validate_board_impl_semantics(
    *,
    zf: ZipFile,
    rel_to_name: dict[str, str],
) -> str | None:
    impl, err = parse_required_json(
        zf=zf,
        rel_to_name=rel_to_name,
        rel="reports/implementation_gate_summary.json",
    )
    if err is not None:
        return err
    assert impl is not None
    if not bool(impl.get("pass", False)):
        return (
            "proof semantic failure: "
            "implementation_gate_summary pass=false"
        )

    checks = impl.get("checks")
    if not isinstance(checks, dict):
        return (
            "proof semantic failure: "
            "implementation_gate_summary missing checks object"
        )

    for check_name in REQUIRED_IMPL_CHECKS:
        check_data = checks.get(check_name)
        if not isinstance(check_data, dict):
            return (
                "proof semantic failure: "
                f"implementation check missing: {check_name}"
            )
        if not bool(check_data.get("pass", False)):
            return (
                "proof semantic failure: "
                f"implementation check failed: {check_name}"
            )

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release archive.")
    parser.add_argument("archive", help="Path to .zip archive")
    parser.add_argument(
        "--mode",
        choices=["source", "proof", "proof-local", "proof-board"],
        required=True,
        help="Expected archive content mode.",
    )
    parser.add_argument(
        "--strict-proof",
        action="store_true",
        help="Require strict proof artifacts in proof mode.",
    )
    args = parser.parse_args()
    mode = args.mode
    if mode == "proof":
        mode = "proof-local"
    if args.strict_proof and mode == "proof-local":
        mode = "proof-board"

    with ZipFile(args.archive, "r") as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]

        if not names:
            print("archive is empty")
            return 1

        for name in names:
            if unsafe_entry(name):
                print(f"unsafe zip entry: {name}")
                return 1

        ok_root, root_info = single_root(names)
        if not ok_root:
            print(f"archive has multiple roots: {root_info}")
            return 1

        rel_names = [strip_root(n) for n in names if strip_root(n)]
        rel_set = set(rel_names)

        if mode == "source":
            for req in REQUIRED_SOURCE:
                if req not in rel_set:
                    print(f"missing required source entry: {req}")
                    return 1

            for rel in rel_names:
                if any(rel.startswith(p) for p in FORBIDDEN_SOURCE_PREFIXES):
                    print(f"forbidden source entry: {rel}")
                    return 1
                if any(rel.endswith(s) for s in FORBIDDEN_SOURCE_SUFFIXES):
                    print(f"forbidden source entry: {rel}")
                    return 1
                if rel in FORBIDDEN_SOURCE_EXACT:
                    print(f"forbidden source entry: {rel}")
                    return 1
                if rel.endswith("/.DS_Store"):
                    print(f"forbidden source entry: {rel}")
                    return 1
                if rel.startswith("dist/") and rel.endswith(".zip"):
                    print(f"forbidden source entry: {rel}")
                    return 1
                if rel.endswith(".log") and not rel.startswith("reports/"):
                    print(f"forbidden source entry: {rel}")
                    return 1

        else:
            required_proof = list(REQUIRED_PROOF_LOCAL)
            if mode == "proof-board":
                required_proof.extend(REQUIRED_PROOF_BOARD)

            for req in required_proof:
                if req not in rel_set:
                    print(f"missing required proof entry: {req}")
                    return 1

            rel_to_name = {
                strip_root(name): name
                for name in names
                if strip_root(name)
            }
            semantic_error = validate_preboard_semantics(
                zf=zf,
                rel_to_name=rel_to_name,
            )
            if semantic_error is not None:
                print(semantic_error)
                return 1

            if mode == "proof-board":
                semantic_error = validate_board_impl_semantics(
                    zf=zf,
                    rel_to_name=rel_to_name,
                )
                if semantic_error is not None:
                    print(semantic_error)
                    return 1

    print(f"archive valid mode={mode} entries={len(rel_names)}")
    print(f"archive root={root_info}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
