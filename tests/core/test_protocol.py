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
    ProtocolError,
    ProtocolFrame,
    TruncatedFrameError,
    UnsupportedProtocolVersion,
    decode_frame,
    encode_frame,
    sequence_is_after,
    timestamp_is_after,
)

GOLDEN_FIXTURE = Path(__file__).parents[1] / "fixtures" / "protocol_golden.json"
GOLDEN_VECTORS = json.loads(GOLDEN_FIXTURE.read_text(encoding="utf-8"))["vectors"]


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
            "unit": "m/s^2",
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

    corrupt_version = bytearray(encode_frame(frame()))
    corrupt_version[4] = GOLDEN_VECTORS["version_skew"]["version"]
    with pytest.raises(IntegrityError, match="checksum"):
        decode_frame(bytes(corrupt_version))

    unsupported = bytearray(encode_frame(frame()))
    unsupported[4] = GOLDEN_VECTORS["version_skew"]["version"]
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
        decode_frame(encoded[: -GOLDEN_VECTORS["truncation"]["remove_bytes"]])
    with pytest.raises(ValueError, match="trailing bytes"):
        decode_frame(encoded + b"extra")


def test_sequence_and_timestamp_order_handle_rollover() -> None:
    vectors = GOLDEN_VECTORS["rollover"]
    assert sequence_is_after(vectors["sequence"]["current"], vectors["sequence"]["previous"])
    assert not sequence_is_after(vectors["sequence"]["previous"], vectors["sequence"]["current"])
    assert timestamp_is_after(
        vectors["timestamp_ns"]["current"], vectors["timestamp_ns"]["previous"]
    )
    assert not timestamp_is_after(
        vectors["timestamp_ns"]["previous"], vectors["timestamp_ns"]["current"]
    )


def test_corruption_vector_and_bounded_error_history() -> None:
    valid = encode_frame(frame())
    corrupt = bytearray(valid)
    corrupt[GOLDEN_VECTORS["corruption"]["offset"]] ^= GOLDEN_VECTORS["corruption"]["xor"]
    with pytest.raises(IntegrityError):
        decode_frame(bytes(corrupt))

    decoder = FrameStreamDecoder()
    valid_tail = encode_frame(frame(sequence=0))
    for _ in range(150):
        decoder.feed(b"noise" + valid_tail)
    assert len(decoder.errors) == 100


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        (FrameKind.SESSION_START, {}),
        (FrameKind.DESCRIPTOR, {"id": "imu.x"}),
        (FrameKind.RECORD, {"signal_id": "imu.x"}),
        (FrameKind.HEARTBEAT, {"uptime_ns": -1, "device_status": {}}),
        (FrameKind.ERROR, {"code": "E1", "message": "bad"}),
        (FrameKind.SESSION_END, {}),
    ],
)
def test_known_frame_kinds_require_valid_payloads(
    kind: FrameKind, payload: dict[str, object]
) -> None:
    with pytest.raises(ProtocolError):
        frame(kind=kind, payload=payload)
