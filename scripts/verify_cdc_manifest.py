#!/usr/bin/env python3
"""Verify CDC manifest requirements against wrapper and cell-match report."""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "constraints" / "cdc_manifest.json"
WRAPPER_PATH = PROJECT_ROOT / "rtl" / "waveform_brain_cdc_wrapper.v"
CELLMATCH_PATH = PROJECT_ROOT / "reports" / "cdc_cell_match_summary.md"

TYPE_MAP = {
    "diagnostic_snapshot": "xpm_cdc_array_single",
}


def required_primitive_types(manifest: dict[str, object]) -> set[str]:
    primitives: set[str] = set()
    for direction in manifest.values():
        if not isinstance(direction, dict):
            continue
        for crossing_type in direction.values():
            if not isinstance(crossing_type, str):
                continue
            primitive = TYPE_MAP.get(crossing_type, crossing_type)
            primitives.add(primitive)
    return primitives


def count_primitive_in_wrapper(wrapper_text: str, primitive: str) -> int:
    return len(re.findall(rf"\b{re.escape(primitive)}\b", wrapper_text))


def report_has_nonzero_match(report_text: str, primitive: str) -> bool:
    primitive_lc = primitive.lower()
    for line in report_text.splitlines():
        row = line.strip()
        if not row.startswith("|"):
            continue
        cols = [col.strip().strip("`") for col in row.strip("|").split("|")]
        if len(cols) < 2:
            continue
        row_lc = " ".join(cols).lower()
        if primitive_lc not in row_lc:
            continue
        raw_count = cols[1]
        try:
            count = int(raw_count, 0)
        except ValueError:
            continue
        if count > 0:
            return True
    return False


def main() -> int:
    if not MANIFEST_PATH.exists():
        rel_manifest = MANIFEST_PATH.relative_to(PROJECT_ROOT)
        print(f"cdc-manifest-fail: missing {rel_manifest}")
        return 1
    if not WRAPPER_PATH.exists():
        rel_wrapper = WRAPPER_PATH.relative_to(PROJECT_ROOT)
        print(f"cdc-manifest-fail: missing {rel_wrapper}")
        return 1
    if not CELLMATCH_PATH.exists():
        rel_cellmatch = CELLMATCH_PATH.relative_to(PROJECT_ROOT)
        print(f"cdc-manifest-fail: missing {rel_cellmatch}")
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        print("cdc-manifest-fail: manifest must be a JSON object")
        return 1

    wrapper_text = WRAPPER_PATH.read_text(encoding="utf-8")
    report_text = CELLMATCH_PATH.read_text(encoding="utf-8")

    failures: list[str] = []
    for primitive in sorted(required_primitive_types(manifest)):
        wrapper_count = count_primitive_in_wrapper(wrapper_text, primitive)
        if wrapper_count == 0:
            failures.append(
                f"required primitive missing in wrapper: {primitive}"
            )
            continue
        if not report_has_nonzero_match(report_text, primitive):
            failures.append(
                "required primitive has zero/missing cell "
                f"matches: {primitive}"
            )

    if failures:
        print("cdc-manifest-fail")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("cdc-manifest-pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
