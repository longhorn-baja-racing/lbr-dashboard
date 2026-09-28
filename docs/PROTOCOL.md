# LBR telemetry and log protocol

This is the canonical versioned contract between firmware, native SD logs, and
the dashboard. Firmware host tests should consume the same golden vectors and
link back to this document.

## Version and transport

The protocol name is `lbr.telemetry`; the current protocol version is `1`.
An `.lbrlog` native session file is a concatenation of protocol frames. A live
transport may split or combine those frames however it needs; it does not need
to use the SD file's storage boundaries.

Each frame is little-endian binary data. Decoders verify CRC32 before acting
on the version byte, so a damaged version byte is reported as corruption;
version-skew errors are reserved for intact frames:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | Magic `LBR1` |
| 4 | 1 | Protocol version |
| 5 | 1 | Frame kind |
| 6 | 1 | Flags (unknown bits are ignored) |
| 7 | 1 | Reserved, must be zero when writing |
| 8 | 4 | Packet sequence, unsigned, wraps at `2^32` |
| 12 | 8 | Device monotonic timestamp in nanoseconds, wraps at `2^64` |
| 20 | 4 | Payload length in bytes |
| 24 | N | Canonical UTF-8 JSON object payload |
| 24 + N | 4 | CRC32 of header plus payload |

The maximum payload is 16 MiB. CRC32 is unsigned little-endian. A decoder
must reject oversized lengths before allocating based on them.

## Frame kinds and payloads

Kinds `1` through `6` are `session_start`, `descriptor`, `record`,
`heartbeat`, `error`, and `session_end`. Unknown kinds remain inspectable and
must not be interpreted as a known kind.

Known frame kinds have these required JSON payload fields and types; additional
fields are allowed for forward compatibility:

| Kind | Required fields and types |
| --- | --- |
| `session_start` | `session_id`: non-empty string; `protocol_version`: integer 1–255; `schema`: object; `descriptors`: array of descriptor objects |
| `descriptor` | `id`, `display_name`, `type`, `source_id`: non-empty strings; `path`: non-empty array of non-empty strings. Other descriptor fields follow `core/signals.py`. |
| `record` | `signal_id`: non-empty string; `value`: any JSON value. Optional `unit` and `quality` are non-empty strings; optional `available` is boolean. |
| `heartbeat` | `uptime_ns`: unsigned 64-bit integer; `device_status`: object |
| `error` | `code`, `message`: non-empty strings; `recoverable`: boolean |
| `session_end` | `reason`: non-empty string |

An unavailable record still includes `value` (use JSON `null`) and sets
`available` to `false`. Unknown frame kinds remain opaque JSON objects.

One record represents one signal sample. Mixed-rate signals therefore remain
sparse; the protocol never invents duplicate or interpolated rows. Full-rate
SD logging is authoritative even when live telemetry is downsampled.

`timestamp_ns` is always device monotonic measurement time. Laptop arrival time
may be attached by the dashboard as diagnostic metadata, but it is never used
as measurement time and is never written over this field. Packet ordering uses
the half-range modulo rule for sequence and timestamp rollover.

## Corruption, truncation, and compatibility

The stream decoder searches for the next `LBR1` magic after discarded bytes.
It waits for a complete header and declared payload, verifies CRC32 before
checking protocol support, and emits valid frames only. On a bad checksum,
malformed JSON, invalid payload, unsupported version, or oversized length it
records an error and advances to the next possible magic. It retains only the
most recent 100 errors. A truncated final frame is recoverable: completed
prior frames remain usable and the tail is reported when the stream closes.

The shared `tests/fixtures/protocol_golden.json` vectors define a corrupted
version byte, a one-byte truncated tail, unsupported version 2, and 32-bit
sequence / 64-bit timestamp rollover pairs. Firmware host tests should apply
the same mutations and boundary values.

Readers must accept older supported protocol versions and skip or preserve
unknown JSON fields. Unknown frame kinds may be logged and skipped. An
unsupported version must produce an actionable error naming the version; it
must not be silently decoded as another version. Writers emit only the current
version and must not assign meaning to fields they do not define.

The protocol intentionally does not define vehicle-subsystem semantics for
GP9. Those semantics belong in a future descriptor or firmware contract.

