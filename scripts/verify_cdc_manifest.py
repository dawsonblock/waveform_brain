#!/usr/bin/env python3
"""Verify CDC manifest requirements against wrapper and cell-match report."""

from __future__ import annotations

import argparse
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


def normalize_entry(
    crossing_name: str,
    crossing_spec: object,
) -> tuple[str, str, str] | None:
    primitive: str | None = None
    instance: str | None = None

    if isinstance(crossing_spec, str):
        primitive = crossing_spec
    elif isinstance(crossing_spec, dict):
        raw_primitive = crossing_spec.get("primitive")
        raw_instance = crossing_spec.get("wrapper_instance")
        if isinstance(raw_primitive, str):
            primitive = raw_primitive
        if isinstance(raw_instance, str):
            instance = raw_instance

    if not primitive:
        return None

    primitive = TYPE_MAP.get(primitive, primitive)
    return crossing_name, primitive, instance or ""


def required_crossings(
    manifest: dict[str, object],
) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for direction in manifest.values():
        if not isinstance(direction, dict):
            continue
        for crossing_name, crossing_spec in direction.items():
            if not isinstance(crossing_name, str):
                continue
            normalized = normalize_entry(crossing_name, crossing_spec)
            if normalized is not None:
                entries.append(normalized)
    return entries


def required_primitive_types(manifest: dict[str, object]) -> set[str]:
    primitives: set[str] = set()
    for _, primitive, _ in required_crossings(manifest):
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
    parser = argparse.ArgumentParser(description="Verify CDC manifest")
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Skip cdc_cell_match_summary.md checks.",
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        rel_manifest = MANIFEST_PATH.relative_to(PROJECT_ROOT)
        print(f"cdc-manifest-fail: missing {rel_manifest}")
        return 1
    if not WRAPPER_PATH.exists():
        rel_wrapper = WRAPPER_PATH.relative_to(PROJECT_ROOT)
        print(f"cdc-manifest-fail: missing {rel_wrapper}")
        return 1
    if not args.static_only and not CELLMATCH_PATH.exists():
        rel_cellmatch = CELLMATCH_PATH.relative_to(PROJECT_ROOT)
        print(f"cdc-manifest-fail: missing {rel_cellmatch}")
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        print("cdc-manifest-fail: manifest must be a JSON object")
        return 1

    wrapper_text = WRAPPER_PATH.read_text(encoding="utf-8")
    report_text = ""
    if not args.static_only:
        report_text = CELLMATCH_PATH.read_text(encoding="utf-8")

    failures: list[str] = []
    for crossing_name, primitive, instance in required_crossings(manifest):
        if count_primitive_in_wrapper(wrapper_text, primitive) == 0:
            failures.append(
                "required primitive missing in wrapper: "
                f"{crossing_name} -> {primitive}"
            )
            continue
        if instance and instance not in wrapper_text:
            failures.append(
                "required wrapper instance missing: "
                f"{crossing_name} -> {instance}"
            )

    if not args.static_only:
        for primitive in sorted(required_primitive_types(manifest)):
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
