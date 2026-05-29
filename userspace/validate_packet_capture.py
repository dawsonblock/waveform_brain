#!/usr/bin/env python3
"""
Validate a text dump of Waveform Brain AXI-Stream packet words.

Input formats:
  - one hex 64-bit word per line
  - whitespace-separated hex words
  - optional 0x prefix

Checks:
  - two-beat packet alignment
  - supported packet version
  - syndrome range
  - optional monotonic sequence counter
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from packet_parser import iter_packet_records, validate_monotonic_sequences


HEX_RE = re.compile(r"(?:0x)?[0-9a-fA-F]{1,16}")


def load_words(path: Path) -> list[int]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    words = []
    for match in HEX_RE.finditer(text):
        token = match.group(0)
        words.append(int(token, 16))
    return words


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Waveform Brain packet capture.")
    parser.add_argument("capture", type=Path)
    parser.add_argument("--no-seq-check", action="store_true")
    args = parser.parse_args()

    words = load_words(args.capture)
    if len(words) % 2 != 0:
        print(f"FAIL: odd number of 64-bit words: {len(words)}")
        return 1

    try:
        records = list(iter_packet_records(words))
    except Exception as exc:
        print(f"FAIL: parse error: {exc}")
        return 1

    errors = []
    if not args.no_seq_check:
        errors.extend(validate_monotonic_sequences(records))

    for idx, rec in enumerate(records):
        if any(s < 0 or s > 3 for s in rec.syndromes):
            errors.append(f"packet {idx}: syndrome out of range")
        if rec.version not in (1, 2):
            errors.append(f"packet {idx}: unsupported version {rec.version}")

    print(f"words: {len(words)}")
    print(f"packets: {len(records)}")
    if records:
        print(f"first_sequence: {records[0].sequence}")
        print(f"last_sequence: {records[-1].sequence}")
        print(f"fault_packets: {sum(1 for r in records if r.fault)}")

    if errors:
        print("FAIL:")
        for err in errors[:50]:
            print(f"  {err}")
        return 1

    print("PASS: capture is structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
