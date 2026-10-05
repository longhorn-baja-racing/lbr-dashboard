# ADR 0002: Versioned schema-driven telemetry protocol

## Status

Accepted for P0 issue #19.

## Decision

Use a versioned binary frame with a fixed header, device monotonic timestamp,
packet sequence, bounded JSON payload, and CRC32 integrity trailer. Use the
same frames in the authoritative full-rate native session/log container and
allow live transports to provide different packetization around those frames.

Signal descriptors and records remain schema-driven so mixed-rate and future
signals do not require a new fixed vehicle struct. The dashboard's host arrival
time is diagnostic-only.

## Consequences

- Firmware and dashboard can share exact golden frame vectors.
- Corruption and truncated-tail recovery have deterministic, bounded behavior.
- Unknown fields and frame kinds can survive forward evolution.
- A future major protocol version requires an explicit decoder update.
- Transport policy for Pico, LoRa, and CAN remains outside this contract.
- GP9 receives no invented meaning from the protocol layer.

See [`docs/PROTOCOL.md`](../PROTOCOL.md) for the normative field layout and
compatibility rules.

