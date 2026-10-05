"""Golden behavior and failure-boundary tests for the telemetry protocol."""

import json
import struct
from pathlib import Path

import pytest

from lbr_dashboard.core import (
    CURRENT_PROTOCOL_VERSION,
    FrameKind,
    FrameStreamDecoder,
    IntegrityError,
    ProtocolFrame,
    TruncatedFrameError,
    UnsupportedProtocolVersion,
    decode_frame,
    encode_frame,
    sequence_is_after,
    timestamp_is_after,
)

GOLDEN_FIXTURE = Path(__file__).parents[1] / "fixtures" / "protocol_golden.json"


def frame(**overrides: object) -> ProtocolFrame:
    values: dict[str, object] = {
        "version": CURRENT_PROTOCOL_VERSION,
        "kind": FrameKind.RECORD,
        "flags": 0,
        "sequence": 41,
        "timestamp_ns": 12_500,
        "payload": {
            "signal_id": "imu.acceleration.x",
            "value": 1.25,
            "unit": "m/s2",
        },
    }
    values.update(overrides)
    return ProtocolFrame(**values)  # type: ignore[arg-type]


def test_golden_record_round_trip_is_canonical() -> None:
    golden = json.loads(GOLDEN_FIXTURE.read_text(encoding="utf-8"))
    expected = frame(
        version=golden["version"],
        kind=golden["kind"],
        flags=golden["flags"],
        sequence=golden["sequence"],
        timestamp_ns=golden["timestamp_ns"],
        payload=golden["payload"],
    )
    encoded = bytes.fromhex(golden["encoded_hex"])

    assert encoded[:4] == b"LBR1"
    assert decode_frame(encoded) == expected
    assert encode_frame(decode_frame(encoded)) == encoded


def test_unknown_frame_kind_and_payload_fields_are_forward_compatible() -> None:
    unknown = frame(kind=250, payload={"future_field": {"nested": True}})

    decoded = decode_frame(encode_frame(unknown))

    assert decoded.kind_name == "unknown:250"
    assert decoded.payload["future_field"] == {"nested": True}


def test_truncated_tail_is_reported_without_unbounded_buffer_growth() -> None:
    encoded = encode_frame(frame())
    decoder = FrameStreamDecoder(max_buffer_bytes=64)

    assert decoder.feed(encoded[:20]) == ()
    assert decoder.finish()
    assert any("truncated" in error for error in decoder.errors)

    decoder.feed(b"x" * 1000)
    assert len(decoder.errors) >= 2


def test_stream_resynchronizes_after_corruption() -> None:
    first = encode_frame(frame(sequence=1))
    second = encode_frame(frame(sequence=2))
    damaged = bytearray(first)
    damaged[8] ^= 0x01

    decoder = FrameStreamDecoder()
    decoded = decoder.feed(b"noise" + bytes(damaged) + second)

    assert [item.sequence for item in decoded] == [2]
    assert any("checksum" in error or "discarded" in error for error in decoder.errors)


def test_bad_checksum_and_unsupported_version_are_actionable() -> None:
    encoded = bytearray(encode_frame(frame()))
    encoded[-1] ^= 0xFF
    with pytest.raises(IntegrityError, match="checksum"):
        decode_frame(bytes(encoded))

    unsupported = bytearray(encode_frame(frame()))
    unsupported[4] = CURRENT_PROTOCOL_VERSION + 1
    # Recalculate the checksum so the version error is not hidden by integrity.
    payload_length = struct.unpack_from("<I", unsupported, 20)[0]
    checksum_offset = 24 + payload_length
    checksum = __import__("zlib").crc32(unsupported[:checksum_offset]) & 0xFFFFFFFF
    struct.pack_into("<I", unsupported, checksum_offset, checksum)
    with pytest.raises(UnsupportedProtocolVersion, match="unsupported protocol version"):
        decode_frame(bytes(unsupported))


def test_single_frame_decoder_rejects_truncation_and_trailing_bytes() -> None:
    encoded = encode_frame(frame())

    with pytest.raises(TruncatedFrameError):
        decode_frame(encoded[:-1])
    with pytest.raises(ValueError, match="trailing bytes"):
        decode_frame(encoded + b"extra")


def test_sequence_and_timestamp_order_handle_rollover() -> None:
    assert sequence_is_after(0, 2**32 - 1)
    assert not sequence_is_after(2**32 - 1, 0)
    assert timestamp_is_after(0, 2**64 - 1)
    assert not timestamp_is_after(2**64 - 1, 0)
