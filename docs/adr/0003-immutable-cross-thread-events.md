# ADR-0003: Immutable events across the thread boundary, cooperative cancellation

## Status

Proposed — pending review on #17

## Context

Telemetry work does not fit on the UI thread. Parsing a large CSV, decoding a
live stream, and running analysis providers are all long enough to freeze the
interface if run inline. So there will be background threads.

Two failure modes follow, and both are hard to debug:

1. A worker hands the UI a mutable model, keeps a reference, and continues
   writing to it. The UI reads a half-updated object. This produces bugs that
   are timing-dependent, unreproducible, and usually blamed on Qt.
2. A worker touches a widget directly from a non-UI thread. Qt does not support
   this. It fails intermittently rather than immediately, so it survives review
   and testing and appears at competition.

There is also cancellation. Loading a large log and immediately loading a
different one must not leave the first parse running, and application shutdown
must not block on work nobody is waiting for.

## Decision

**All cross-thread payloads are immutable.** Workers emit
`@dataclass(frozen=True)` events. A worker never hands the UI thread an object
it retains a mutable reference to. Where a snapshot of a large buffer would be
expensive to copy, the worker publishes a read-only view and never writes to the
underlying buffer again.

**The UI thread owns all Qt objects.** No other thread constructs, mutates, or
reads a widget. Cross-thread delivery uses queued signal connections.

**Widgets do not spawn threads.** A panel that needs expensive work asks a
service for it. Thread ownership lives in `services` only, which is also the
only layer with a documented shutdown order.

**Cancellation is cooperative and toolkit-agnostic.** Every long-running
operation accepts a `threading.Event` token and checks it between units of work,
at a granularity that keeps response under roughly 100 ms. A cancelled operation
still runs its cleanup and still emits a terminal event, so the UI never waits
on a result that will never arrive.

Shutdown order is: cancel all tokens, join workers, close sources, tear down
widgets.

## Alternatives considered

**Mutable shared model with a lock.** Avoids copying. Rejected because the
correctness of every read then depends on every future contributor remembering
to take the lock, and a missed one fails intermittently. The immutability rule
is checkable by reading a single dataclass declaration.

**`QThread` and Qt's own cancellation primitives throughout.** Idiomatic for a
Qt application. Rejected for the token specifically: `threading.Event` lets
`services` be unit-tested without a `QApplication`, which keeps the cancellation
tests in the fast PR gate rather than requiring an event loop. Qt threading is
still used where a worker must live in the Qt object tree.

**Preemptive cancellation.** Not available in Python for threads, and not
desirable — cleanup would not run.

## Consequences

- A whole class of race condition is unavailable by construction rather than
  avoided by discipline.
- Cancellation logic is testable with plain `pytest` and no display server,
  which matters for the headless PR gate in #26.
- The shared clock (#22) and analysis providers (#23) inherit a single
  cancellation contract instead of each inventing one.
- Cost: immutable snapshots mean copying. For high-rate telemetry this needs
  attention — the performance budgets in #27 should include the per-update
  allocation cost, and coarse-grained batched events are preferred over
  per-sample events.
- Cost: cooperative cancellation means a worker in a tight loop that never
  checks its token cannot be stopped. Every worker needs a check in its inner
  loop, and that is a review item, not something CI can catch.