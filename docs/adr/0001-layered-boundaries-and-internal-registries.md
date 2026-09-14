# ADR 0001: Layered boundaries and internal registries

- Status: Accepted
- Date: 2026-09-04
- Scope: P0 issue #17

## Decision

Keep framework-neutral contracts and lifecycle primitives in `core`, keep
provider implementations behind typed internal registries, and make `app`
the only composition root. The UI receives an application-owned registry
bundle but does not discover or instantiate concrete telemetry providers.

Background services communicate with their owner through immutable queued
events and cooperative cancellation. Qt objects remain on the UI thread.

## Why

The dashboard must support arbitrary signals and future transports without
making the data model depend on widgets or making every new provider require a
shell edit. Per-application registries preserve explicit ownership and avoid
the hidden state of service locators or global singletons.

## Consequences

- New providers need a typed contract and a registration entry in the
  composition code, not a change to existing UI code.
- Registry IDs and failure behavior are testable and deterministic.
- Later milestones must preserve the documented import directions.
- There is no public plugin SDK or dynamic untrusted code loading in this
  milestone.
