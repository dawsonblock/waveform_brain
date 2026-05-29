"""
packet_parser.py

Utilities for parsing Waveform Brain AXI-Stream packets.

Supported packet versions:
- v1: two-beat packet with metadata in beat1[63:48], no sequence field.
- v2: two-beat packet with metadata in beat1[63:48]
    and sequence in beat1[31:0].
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List, Tuple

SUPPORTED_PACKET_VERSIONS = {1, 2}
CURRENT_PACKET_VERSION = 2


@dataclass(frozen=True)
class PacketRecord:
    version: int
    data: List[int]
    syndromes: List[int]
    fault: bool
    sequence: int | None
    raw_words: Tuple[int, int]


def _u16_to_i16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def parse_packet_record(
    words: List[int], *, signed: bool = False
) -> PacketRecord:
    if not isinstance(words, (list, tuple)) or len(words) != 2:
        raise ValueError(
            "parse_packet_record expects a list/tuple of two 64-bit words"
        )

    data_word = int(words[0]) & 0xFFFFFFFFFFFFFFFF
    meta_word = int(words[1]) & 0xFFFFFFFFFFFFFFFF

    raw_data = [
        data_word & 0xFFFF,
        (data_word >> 16) & 0xFFFF,
        (data_word >> 32) & 0xFFFF,
        (data_word >> 48) & 0xFFFF,
    ]
    data = [_u16_to_i16(x) for x in raw_data] if signed else raw_data

    meta = (meta_word >> 48) & 0xFFFF
    version = (meta >> 12) & 0xF
    if version == 0:
        # Backward compatibility for legacy packets that omitted the explicit
        # version nibble and encoded only fault/syndrome fields.
        version = 1
    if version not in SUPPORTED_PACKET_VERSIONS:
        raise ValueError(f"unsupported packet format version: {version}")

    fault = bool((meta >> 8) & 0x1)
    syndromes = [
        meta & 0x3,
        (meta >> 2) & 0x3,
        (meta >> 4) & 0x3,
        (meta >> 6) & 0x3,
    ]

    sequence = (meta_word & 0xFFFFFFFF) if version >= 2 else None

    return PacketRecord(
        version=version,
        data=data,
        syndromes=syndromes,
        fault=fault,
        sequence=sequence,
        raw_words=(data_word, meta_word),
    )


def parse_packet(
    words: List[int], *, signed: bool = False
) -> Tuple[List[int], List[int], bool]:
    """Backward-compatible tuple parser.

    Returns data, syndromes, fault. Use parse_packet_record() for version and
    sequence number.
    """
    rec = parse_packet_record(words, signed=signed)
    return rec.data, rec.syndromes, rec.fault


def iter_packet_records(
    words: Iterable[int], *, signed: bool = False
) -> Iterator[PacketRecord]:
    buf: List[int] = []
    for word in words:
        buf.append(int(word))
        if len(buf) == 2:
            yield parse_packet_record(buf, signed=signed)
            buf.clear()
    if buf:
        raise ValueError("truncated packet: odd number of 64-bit words")


def iter_packets(
    words: Iterable[int],
) -> Iterator[Tuple[List[int], List[int], bool]]:
    for rec in iter_packet_records(words):
        yield rec.data, rec.syndromes, rec.fault


def validate_monotonic_sequences(records: Iterable[PacketRecord]) -> list[str]:
    errors: list[str] = []
    last_seq: int | None = None
    for idx, rec in enumerate(records):
        if rec.sequence is None:
            continue
        if last_seq is not None:
            expected = (last_seq + 1) & 0xFFFFFFFF
            if rec.sequence != expected:
                errors.append(
                    (
                        f"packet {idx}: sequence {rec.sequence} "
                        f"!= expected {expected}"
                    )
                )
        last_seq = rec.sequence
    return errors


if __name__ == "__main__":
    example = [
        0x0004000300020001,
        0x2102000000000007,
    ]
    print(parse_packet_record(example))
