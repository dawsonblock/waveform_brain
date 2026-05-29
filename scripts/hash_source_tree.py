#!/usr/bin/env python3
"""Compute and emit deterministic source-tree hash for proof checks."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INCLUDE = [
    "rtl",
    "sim",
    "scripts",
    "tests",
    "userspace",
    "firmware",
    "constraints",
    "Makefile",
]
DEFAULT_EXCLUDES = {
    "reports",
    "dist",
    "build",
    "build_dir",
    "sim/build",
}
DEFAULT_EXACT_EXCLUDES = {
    "rtl/reciprocal_lut_w16_q24w25.mem",
    "sim/gkp_cosim_vectors.hex",
    "register_map.json",
    "register_map.md",
    "register_map_issues.log",
    "cdc_crossing_suggestions.json",
    "cdc_crossing_suggestions.md",
}
DEFAULT_SUFFIX_EXCLUDES = {".pyc", ".vcd", ".fst"}


def _is_excluded(rel: Path) -> bool:
    rel_str = rel.as_posix()
    if rel_str in DEFAULT_EXACT_EXCLUDES:
        return True
    if any(
        rel_str == p or rel_str.startswith(f"{p}/")
        for p in DEFAULT_EXCLUDES
    ):
        return True
    if any(part == "__pycache__" for part in rel.parts):
        return True
    if rel.suffix in DEFAULT_SUFFIX_EXCLUDES:
        return True
    return False


def iter_source_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    for item in DEFAULT_INCLUDE:
        p = project_root / item
        if not p.exists():
            continue
        if p.is_file():
            rel = p.relative_to(project_root)
            if not _is_excluded(rel):
                files.append(p)
            continue
        for child in p.rglob("*"):
            if not child.is_file():
                continue
            rel = child.relative_to(project_root)
            if _is_excluded(rel):
                continue
            files.append(child)
    return sorted(set(files))


def compute_source_tree_hash(project_root: Path) -> str:
    h = hashlib.sha256()
    for f in iter_source_files(project_root):
        rel = f.relative_to(project_root).as_posix().encode("utf-8")
        h.update(rel)
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute source-tree hash")
    parser.add_argument("--out-txt", default="reports/source_tree_hash.txt")
    parser.add_argument(
        "--out-json",
        default="reports/source_tree_hash_summary.json",
    )
    parser.add_argument(
        "--command",
        default="python3 scripts/hash_source_tree.py",
    )
    args = parser.parse_args()

    source_hash = compute_source_tree_hash(PROJECT_ROOT)
    out_txt = PROJECT_ROOT / args.out_txt
    out_json = PROJECT_ROOT / args.out_json
    out_txt.parent.mkdir(parents=True, exist_ok=True)

    out_txt.write_text(source_hash + "\n", encoding="utf-8")

    payload = {
        "schema_version": 1,
        "pass": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": args.command,
        "source_tree_hash": source_hash,
        "log_file": str(out_txt.relative_to(PROJECT_ROOT).as_posix()),
    }
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"source_tree_hash={source_hash}")
    print(f"Wrote {out_txt}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
