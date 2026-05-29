#!/usr/bin/env python3
"""Validate source/proof release archives for safety and required content."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import PurePosixPath
from zipfile import ZipFile

REQUIRED_SOURCE = [
    "Makefile",
    "README.md",
    "rtl/axilite_regfile_full.v",
    "scripts/preboard_check.py",
    "board_tests/run_board_smoke.py",
    "board_tests/adapter_contract.py",
    "tests/test_board_smoke_scaffold.py",
    "tests/test_axilite_regfile_static.py",
]

FORBIDDEN_SOURCE_PREFIXES = [
    "__MACOSX/",
    "sim/build/",
    "build_dir/",
    "reports/",
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
    "reports/gkp_decoder_sim_summary.json",
    "reports/rtl_arithmetic_audit.json",
    "reports/rtl_arithmetic_audit.md",
    "reports/rtl_arithmetic_audit.log",
    "reports/rtl_sanity.log",
    "reports/release_prereq_summary_local.json",
    "reports/proof_manifest_local.json",
]

REQUIRED_PROOF_BOARD = [
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
    "reports/unittest.log",
    "reports/make_validate.log",
    "reports/vivado_synth.log",
    "reports/vivado_impl.log",
    "reports/release_prereq_summary_board.json",
    "reports/proof_manifest_board.json",
]

REQUIRED_IMPL_CHECKS = [
    "cdc_critical",
    "cdc_cell_match",
    "timing",
    "drc",
]

REQUIRED_PROOF_PASS_JSONS = [
    "reports/preboard_local_summary.json",
    "reports/local_toolchain_summary.json",
    "reports/source_tree_hash_summary.json",
    "reports/source_tree_clean_summary.json",
    "reports/cdc_static_summary.json",
    "reports/axilite_regfile_sim_summary.json",
    "reports/packer_axis_sim_summary.json",
    "reports/safety_monitor_sim_summary.json",
    "reports/prbs_datapath_sim_summary.json",
    "reports/gkp_decoder_sim_summary.json",
]

REQUIRED_METADATA_FIELDS = [
    "generated_at_utc",
    "command",
]

HASH_CANONICAL_SUMMARY = "reports/source_tree_hash_summary.json"
HASH_TEXT_FILE = "reports/source_tree_hash.txt"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def _read_json_or_error(
    *,
    zf: ZipFile,
    rel_to_name: dict[str, str],
    rel: str,
) -> tuple[dict[str, object] | None, str | None]:
    data, err = parse_required_json(zf=zf, rel_to_name=rel_to_name, rel=rel)
    if err is not None:
        return None, err
    assert data is not None
    return data, None


def validate_common_summary_metadata(
    *,
    zf: ZipFile,
    rel_to_name: dict[str, str],
    rel: str,
) -> str | None:
    payload, err = _read_json_or_error(zf=zf, rel_to_name=rel_to_name, rel=rel)
    if err is not None:
        return err
    assert payload is not None

    for field in REQUIRED_METADATA_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            return (
                f"proof semantic failure: {rel} "
                f"missing metadata field {field}"
            )

    if not (
        isinstance(payload.get("source_tree_hash"), str)
        and payload.get("source_tree_hash")
    ) and not (
        isinstance(payload.get("source_sha256"), str)
        and payload.get("source_sha256")
    ):
        return (
            "proof semantic failure: "
            f"{rel} missing source_tree_hash/source_sha256"
        )

    return None


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

    if not bool(preboard.get("overall_pass", False)):
        return (
            "proof semantic failure: "
            "preboard_local_summary overall_pass=false"
        )

    return None


def validate_proof_local_semantics(
    *,
    zf: ZipFile,
    rel_to_name: dict[str, str],
) -> str | None:
    canonical_hash = ""
    canonical_summary, err = _read_json_or_error(
        zf=zf,
        rel_to_name=rel_to_name,
        rel=HASH_CANONICAL_SUMMARY,
    )
    if err is not None:
        return err
    assert canonical_summary is not None
    hash_val = canonical_summary.get("source_tree_hash")
    if isinstance(hash_val, str):
        canonical_hash = hash_val.strip()
    if not canonical_hash:
        return (
            "proof semantic failure: "
            "reports/source_tree_hash_summary.json missing source_tree_hash"
        )

    txt_name = rel_to_name.get(HASH_TEXT_FILE)
    if txt_name is None:
        return f"missing required proof entry: {HASH_TEXT_FILE}"
    txt_val = zf.read(txt_name).decode("utf-8", errors="replace").strip()
    if txt_val != canonical_hash:
        return (
            "proof freshness failure: "
            f"{HASH_TEXT_FILE} does not match {HASH_CANONICAL_SUMMARY}"
        )

    for rel in REQUIRED_PROOF_PASS_JSONS:
        payload, err = _read_json_or_error(
            zf=zf,
            rel_to_name=rel_to_name,
            rel=rel,
        )
        if err is not None:
            return err
        assert payload is not None
        if not bool(payload.get("pass", False)):
            return f"proof semantic failure: {rel} pass=false"
        metadata_err = validate_common_summary_metadata(
            zf=zf,
            rel_to_name=rel_to_name,
            rel=rel,
        )
        if metadata_err is not None:
            return metadata_err

        payload_hash = payload.get("source_tree_hash")
        payload_sha = payload.get("source_sha256")
        current_hash = ""
        if isinstance(payload_hash, str) and payload_hash.strip():
            current_hash = payload_hash.strip()
        elif isinstance(payload_sha, str) and payload_sha.strip():
            current_hash = payload_sha.strip()

        if current_hash and current_hash != canonical_hash:
            return (
                "proof freshness failure: "
                f"{rel} hash mismatch vs {HASH_CANONICAL_SUMMARY}"
            )

    if (
        rel_to_name.get("reports/register_map.json") is None
        and rel_to_name.get("register_map.json") is None
    ):
        return "missing required proof entry: reports/register_map.json"

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


def validate_prereq_summary_semantics(
    *,
    zf: ZipFile,
    rel_to_name: dict[str, str],
    mode: str,
) -> str | None:
    rel = "reports/release_prereq_summary_local.json"
    expected_mode = "proof-local"
    if mode == "proof-board":
        rel = "reports/release_prereq_summary_board.json"
        expected_mode = "proof-board"

    payload, err = _read_json_or_error(
        zf=zf,
        rel_to_name=rel_to_name,
        rel=rel,
    )
    if err is not None:
        return err
    assert payload is not None

    if not bool(payload.get("pass", False)):
        return f"proof semantic failure: {rel} pass=false"

    actual_mode = payload.get("mode")
    if actual_mode != expected_mode:
        return (
            "proof semantic failure: "
            f"{rel} mode mismatch (expected {expected_mode})"
        )

    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        return f"proof semantic failure: {rel} missing checks list"

    return None


def validate_proof_manifest_semantics(
    *,
    zf: ZipFile,
    rel_to_name: dict[str, str],
    rel_set: set[str],
    mode: str,
) -> str | None:
    rel = "reports/proof_manifest_local.json"
    expected_mode = "proof-local"
    if mode == "proof-board":
        rel = "reports/proof_manifest_board.json"
        expected_mode = "proof-board"

    payload, err = _read_json_or_error(
        zf=zf,
        rel_to_name=rel_to_name,
        rel=rel,
    )
    if err is not None:
        return err
    assert payload is not None

    if not bool(payload.get("pass", False)):
        return f"proof semantic failure: {rel} pass=false"

    actual_mode = payload.get("mode")
    if actual_mode != expected_mode:
        return (
            "proof semantic failure: "
            f"{rel} mode mismatch (expected {expected_mode})"
        )

    manifest_hash = payload.get("source_tree_hash")
    if not isinstance(manifest_hash, str) or not manifest_hash.strip():
        return f"proof semantic failure: {rel} missing source_tree_hash"

    canonical_summary, err = _read_json_or_error(
        zf=zf,
        rel_to_name=rel_to_name,
        rel=HASH_CANONICAL_SUMMARY,
    )
    if err is not None:
        return err
    assert canonical_summary is not None
    canonical_hash = canonical_summary.get("source_tree_hash")
    if not isinstance(canonical_hash, str) or not canonical_hash.strip():
        return (
            "proof semantic failure: "
            f"{HASH_CANONICAL_SUMMARY} missing source_tree_hash"
        )

    if manifest_hash.strip() != canonical_hash.strip():
        return (
            "proof freshness failure: "
            f"{rel} hash mismatch vs {HASH_CANONICAL_SUMMARY}"
        )

    file_count = payload.get("required_file_count")
    files = payload.get("files")
    if not isinstance(file_count, int) or file_count <= 0:
        return f"proof semantic failure: {rel} invalid required_file_count"
    if not isinstance(files, list) or len(files) != file_count:
        return (
            "proof semantic failure: "
            f"{rel} files length mismatch vs required_file_count"
        )

    manifest_paths: set[str] = set()
    for index, file_entry in enumerate(files):
        if not isinstance(file_entry, dict):
            return (
                "proof semantic failure: "
                f"{rel} files[{index}] is not an object"
            )
        entry_path = file_entry.get("path")
        entry_size = file_entry.get("size")
        entry_sha256 = file_entry.get("sha256")
        if not isinstance(entry_path, str) or not entry_path:
            return (
                "proof semantic failure: "
                f"{rel} files[{index}] missing path"
            )
        if unsafe_entry(entry_path):
            return (
                "proof semantic failure: "
                f"{rel} invalid listed path {entry_path}"
            )
        if not isinstance(entry_size, int) or entry_size < 0:
            return (
                "proof semantic failure: "
                f"{rel} invalid size for {entry_path}"
            )
        if not isinstance(entry_sha256, str) or len(entry_sha256) != 64:
            return (
                "proof semantic failure: "
                f"{rel} invalid sha256 for {entry_path}"
            )
        if entry_path in manifest_paths:
            return (
                "proof semantic failure: "
                f"{rel} duplicate listed path {entry_path}"
            )

        archive_name = rel_to_name.get(entry_path)
        if archive_name is None:
            return (
                "proof semantic failure: "
                f"{rel} lists missing file {entry_path}"
            )
        file_bytes = zf.read(archive_name)
        if len(file_bytes) != entry_size:
            return (
                "proof semantic failure: "
                f"{rel} size mismatch for {entry_path}"
            )
        actual_sha256 = sha256_bytes(file_bytes)
        if actual_sha256 != entry_sha256.lower():
            return (
                "proof semantic failure: "
                f"{rel} hash mismatch for {entry_path}"
            )
        manifest_paths.add(entry_path)

    allowed_extra_paths = {rel}
    if mode == "proof-board":
        allowed_extra_paths.add("reports/proof_manifest_local.json")

    for archive_path in rel_set:
        if archive_path in manifest_paths:
            continue
        if archive_path in allowed_extra_paths:
            continue
        return (
            "proof semantic failure: "
            f"{rel} does not list archive file {archive_path}"
        )

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release archive.")
    parser.add_argument("archive", help="Path to .zip archive")
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
    if mode == "board-impl":
        mode = "proof-board"
    if mode == "board-capture":
        mode = "proof-board"
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

            semantic_error = validate_proof_local_semantics(
                zf=zf,
                rel_to_name=rel_to_name,
            )
            if semantic_error is not None:
                print(semantic_error)
                return 1

            semantic_error = validate_prereq_summary_semantics(
                zf=zf,
                rel_to_name=rel_to_name,
                mode=mode,
            )
            if semantic_error is not None:
                print(semantic_error)
                return 1

            semantic_error = validate_proof_manifest_semantics(
                zf=zf,
                rel_to_name=rel_to_name,
                rel_set=rel_set,
                mode=mode,
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
