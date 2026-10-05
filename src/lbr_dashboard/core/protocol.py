"""Versioned, schema-driven framing for live telemetry and native log files.

The codec deliberately carries opaque JSON payloads.  Signal meaning belongs to
the signal schema from :mod:`lbr_dashboard.core.signals`, so adding a sensor
does not require changing this transport/container layer.
"""

from __future__ import annotations

import json
import struct
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from types import MappingProxyType

PROTOCOL_NAME = "lbr.telemetry"
CURRENT_PROTOCOL_VERSION = 1
SUPPORTED_PROTOCOL_VERSIONS = (CURRENT_PROTOCOL_VERSION,)
MAGIC = b"LBR1"
MAX_PAYLOAD_BYTES = 16 * 1024 * 1024
UINT32_MODULUS = 2**32
UINT64_MODULUS = 2**64
_HEADER = struct.Struct("<4sBBBBIQI")
_CHECKSUM = struct.Struct("<I")


class FrameKind(IntEnum):
    """Protocol-level frame types; signal families remain schema-defined."""

    SESSION_START = 1
    DESCRIPTOR = 2
    RECORD = 3
    HEARTBEAT = 4
    ERROR = 5
    SESSION_END = 6


class ProtocolError(ValueError):
    """Base class for malformed or unsupported protocol data."""


class ProtocolDecodeError(ProtocolError):
    """Raised when a complete frame cannot be decoded."""


class UnsupportedProtocolVersion(ProtocolDecodeError):
    """Raised when a frame uses a protocol version this decoder cannot read."""


class TruncatedFrameError(ProtocolDecodeError):
    """Raised when the input ends before a complete frame is available."""


class IntegrityError(ProtocolDecodeError):
    """Raised when a frame checksum does not match its contents."""


def _check_uint(name: str, value: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ProtocolError(f"{name} must be an unsigned integer <= {maximum}")


@dataclass(frozen=True, slots=True)
class ProtocolFrame:
    """A single protocol frame.

    ``timestamp_ns`` is the device monotonic measurement time.  A dashboard
    may attach laptop arrival time as diagnostic metadata outside this object,
    but it must never replace this field.
    """

    version: int
    kind: int
    flags: int
    sequence: int
    timestamp_ns: int
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        _check_uint("version", self.version, 255)
        _check_uint("kind", self.kind, 255)
        _check_uint("flags", self.flags, 255)
        _check_uint("sequence", self.sequence, 2**32 - 1)
        _check_uint("timestamp_ns", self.timestamp_ns, 2**64 - 1)
        if not isinstance(self.payload, Mapping):
            raise ProtocolError("payload must be a JSON object")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    @property
    def kind_name(self) -> str:
        """Return a stable name, including for future frame kinds."""

        try:
            return FrameKind(self.kind).name.lower()
        except ValueError:
            return f"unknown:{self.kind}"


def _payload_bytes(payload: Mapping[str, object]) -> bytes:
    try:
        return json.dumps(
            dict(payload),
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProtocolError("payload must contain only JSON-compatible values") from exc


def encode_frame(frame: ProtocolFrame) -> bytes:
    """Encode one frame as header + canonical JSON payload + CRC32 trailer."""

    payload = _payload_bytes(frame.payload)
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ProtocolError(f"payload exceeds {MAX_PAYLOAD_BYTES} bytes")
    header = _HEADER.pack(
        MAGIC,
        frame.version,
        frame.kind,
        frame.flags,
        0,
        frame.sequence,
        frame.timestamp_ns,
        len(payload),
    )
    checksum = zlib.crc32(header + payload) & 0xFFFFFFFF
    return header + payload + _CHECKSUM.pack(checksum)


def _total_size(data: bytes) -> int:
    if len(data) < _HEADER.size:
        raise TruncatedFrameError("truncated protocol header")
    magic, _version, _kind, _flags, _reserved, _sequence, _timestamp, length = _HEADER.unpack_from(
        data
    )
    if magic != MAGIC:
        raise ProtocolDecodeError("invalid protocol magic")
    if length > MAX_PAYLOAD_BYTES:
        raise ProtocolDecodeError(f"payload exceeds {MAX_PAYLOAD_BYTES} bytes")
    return _HEADER.size + length + _CHECKSUM.size


def decode_frame(
    data: bytes,
    *,
    supported_versions: Sequence[int] = SUPPORTED_PROTOCOL_VERSIONS,
) -> ProtocolFrame:
    """Decode exactly one frame and reject trailing bytes deterministically."""

    total = _total_size(data)
    if len(data) < total:
        raise TruncatedFrameError("truncated protocol payload or checksum")
    if len(data) > total:
        raise ProtocolDecodeError("trailing bytes after protocol frame")

    magic, version, kind, flags, _reserved, sequence, timestamp_ns, length = _HEADER.unpack_from(
        data
    )
    if version not in supported_versions:
        raise UnsupportedProtocolVersion(f"unsupported protocol version {version}")

    payload_end = _HEADER.size + length
    payload_bytes = data[_HEADER.size : payload_end]
    expected = _CHECKSUM.unpack_from(data, payload_end)[0]
    actual = zlib.crc32(data[:payload_end]) & 0xFFFFFFFF
    if actual != expected:
        raise IntegrityError("protocol checksum mismatch")
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolDecodeError("payload is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ProtocolDecodeError("payload must be a JSON object")
    return ProtocolFrame(version, kind, flags, sequence, timestamp_ns, payload)


class FrameStreamDecoder:
    """Incrementally decode concatenated frames and resynchronize after damage."""

    def __init__(
        self,
        *,
        supported_versions: Sequence[int] = SUPPORTED_PROTOCOL_VERSIONS,
        max_buffer_bytes: int = MAX_PAYLOAD_BYTES + _HEADER.size + _CHECKSUM.size,
    ) -> None:
        if max_buffer_bytes < _HEADER.size + _CHECKSUM.size:
            raise ValueError("max_buffer_bytes is too small for a frame")
        self._buffer = bytearray()
        self._errors: list[str] = []
        self._supported_versions = tuple(supported_versions)
        self._max_buffer_bytes = max_buffer_bytes

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(self._errors)

    def feed(self, chunk: bytes) -> tuple[ProtocolFrame, ...]:
        """Consume arbitrary chunks, returning every complete valid frame."""

        self._buffer.extend(chunk)
        if len(self._buffer) > self._max_buffer_bytes:
            self._errors.append("stream buffer exceeded configured limit")
            del self._buffer[: len(self._buffer) - len(MAGIC) + 1]

        frames: list[ProtocolFrame] = []
        while True:
            start = self._buffer.find(MAGIC)
            if start < 0:
                del self._buffer[: -len(MAGIC) + 1]
                break
            if start:
                self._errors.append("discarded bytes before next frame")
                del self._buffer[:start]
            if len(self._buffer) < _HEADER.size:
                break
            try:
                total = _total_size(bytes(self._buffer))
            except TruncatedFrameError:
                break
            except ProtocolDecodeError as exc:
                self._errors.append(str(exc))
                del self._buffer[0]
                continue
            if len(self._buffer) < total:
                break
            candidate = bytes(self._buffer[:total])
            try:
                frames.append(decode_frame(candidate, supported_versions=self._supported_versions))
            except ProtocolDecodeError as exc:
                self._errors.append(str(exc))
                del self._buffer[0]
                continue
            del self._buffer[:total]
        return tuple(frames)

    def finish(self) -> tuple[str, ...]:
        """Report and discard a truncated tail at end-of-stream."""

        if self._buffer:
            self._errors.append("truncated tail at end of stream")
            self._buffer.clear()
        return self.errors


def is_after_modulo(current: int, previous: int, *, bits: int) -> bool:
    """Compare wrapping counters using the half-range ordering rule."""

    if bits not in (32, 64):
        raise ValueError("bits must be 32 or 64")
    modulus = UINT32_MODULUS if bits == 32 else UINT64_MODULUS
    _check_uint("current", current, modulus - 1)
    _check_uint("previous", previous, modulus - 1)
    delta = (current - previous) % modulus
    return 0 < delta < modulus // 2


def sequence_is_after(current: int, previous: int) -> bool:
    """Return whether a packet sequence follows another, including rollover."""

    return is_after_modulo(current, previous, bits=32)


def timestamp_is_after(current: int, previous: int) -> bool:
    """Return whether a device monotonic timestamp follows another."""

    return is_after_modulo(current, previous, bits=64)
