# Architecture

Status: draft for review (#17)

This document describes the production package layout for the dashboard
rebuild: the layers, which layers may import which, and who owns what at
runtime. It reflects the current state. The reasoning behind each decision lives
in [`adr/`](adr/README.md).

---

## 1. Goals

- Adding a signal, a transport, or a panel should not require editing the
  application shell.
- The 2026 sensor set is data, not architecture. No layer above `core` may
  assume a fixed set of signals.
- Background work never blocks the UI thread and never hands the UI thread a
  mutable object.
- Every rule here that can be checked mechanically is checked in CI rather than
  in review.

## 2. Layers

| Layer | May import | Responsibility |
|---|---|---|
| `core` | stdlib only | Signal model, typed protocols, registry machinery, error taxonomy, unit conversion |
| `sources` | `core` | Telemetry acquisition: log importers, live transports, simulator |
| `services` | `core`, `sources` | Session state, playback clock, analysis providers, background workers |
| `ui` | `core`, `services` | PySide6 widgets, PyQtGraph panels, view models |
| `app` | all of the above | Composition root: builds registries, wires dependencies, starts the shell |

Dependencies point downward only. There are no cycles. See
[ADR-0001](adr/0001-layered-architecture.md).

### Forbidden directions (enforced in CI)

| Rule | Rationale |
|---|---|
| `core` must not import `PySide6` or `PyQtGraph` | Core contracts must be testable and reusable without a GUI toolkit |
| `core` must not import `sources`, `services`, `ui`, or `app` | Core is the bottom of the graph |
| `sources` must not import `ui`, `services`, or `app` | Acquisition must not know how data is displayed |
| `services` must not import `ui` or `app` | Analysis must not depend on presentation |
| `ui` must not import `sources` | Panels consume sessions, the coupling most likely to reappear |
| Nothing may import `app` | The composition root is a leaf |

Contracts are declared in `pyproject.toml` and run as part of the PR gate.

### Layer detail

**`core`** holds the schema-driven signal model and the abstract contracts
(`TelemetrySource`, `Importer`, `AnalysisProvider`, `UnitConverter`) as
`typing.Protocol` or ABCs. It also holds the generic `Registry[T]`. No Qt, no
I/O, no threads.

**`sources`** implements acquisition. Each source is a concrete
`TelemetrySource`. This layer owns transport-specific error handling and
translates foreign failures into the `core` error taxonomy at its boundary.

**`services`** owns session lifetime, the shared live/replay clock, and all work
that runs off the UI thread. This is the only layer that creates threads.

**`ui`** is PySide6 and PyQtGraph. Widgets read immutable snapshots and emit
intent. They perform no I/O and own no threads.

**`app`** is the only module that knows every layer exists. It constructs the
registries, populates them, injects them, and owns ordered shutdown.

---

## 3. Registries

Registries are the internal extension mechanism. They are not a public plugin
SDK, and no stability guarantee is offered outside this repository.

### Placement

The generic `Registry[T]` lives in `core.registry` and knows nothing about what
it stores. Concrete registry *instances* live in the layer that owns the
registered type:

| Registry | Defined in | Registers |
|---|---|---|
| Source registry | `sources` | `TelemetrySource` factories |
| Importer registry | `sources` | Log format importers |
| Analysis registry | `services` | `AnalysisProvider` factories |
| Widget registry | `ui` | Widget factories |
| Unit conversion registry | `core` | Pure conversion functions |

This split is what allows `core` to own registry machinery while the widget
registry still holds Qt types. See
[ADR-0002](adr/0002-registry-placement.md).

### Contract

```python
register(entry_id: str, value: T) -> None
get(entry_id: str) -> T
__iter__() -> Iterator[tuple[str, T]]
__contains__(entry_id: str) -> bool
```

Failure behaviour is deterministic and total. No silent overwrite, no `None`
returns:

| Condition | Behaviour |
|---|---|
| Duplicate ID | `DuplicateRegistrationError` at registration time; the first registration wins |
| Unknown ID | `UnknownRegistrationError`, listing the known IDs |
| Empty or non-string ID | `ValueError` - a programming error |
| Factory raises | `RegistryFactoryError`, preserving `__cause__` |
| Iteration | Yields entries sorted by ID |

Iteration order is sorted by ID, never insertion order. Insertion order depends
on import order, which varies by entry point and platform and makes both UI
ordering and test outcomes non-reproducible.

### Ownership

Registries are **constructed in `app` and passed explicitly** to the components
that need them. They are not module-level globals and are not reachable through
a service locator.

- Every test constructs a fresh registry; there is no shared state to reset.
- Registry contents are visible at the composition root rather than accumulated
  as an import side effect.
- Registration is an explicit call in `app`, not an `__init_subclass__` hook or
  an import-time decorator.

---

## 4. Lifecycle and ownership

| Object | Owner | Lifetime |
|---|---|---|
| Registries | `app` | Process lifetime, populated once at startup |
| Active session | `services` | From source open to source close |
| Telemetry source | `services` (the session) | Owned by the session that opened it |
| Background workers | `services` | Scoped to the operation; joined before session teardown |
| Widgets | `ui`, via the Qt parent tree | Owned by the shell |

Rules:

- The creator of a resource closes it. A source is closed by the session that
  opened it, not by the UI that requested the open.
- Shutdown is ordered: cancel tokens, join workers, close sources, tear down
  widgets.
- No object reaches upward. A source never calls into the UI; it emits events
  that `services` forwards.

---

## 5. Threading

See [ADR-0003](adr/0003-immutable-cross-thread-events.md).

- **The UI thread owns all Qt objects.** No other thread constructs, mutates, or
  reads a widget.
- Background work runs in `services` and reports results as immutable events.
- All cross-thread payloads are `@dataclass(frozen=True)`.
- Cross-thread delivery uses queued signal connections.
- Widgets do not spawn threads. A panel needing expensive work asks a service.

---

## 6. Error propagation

Three categories, distinguished by who is expected to handle them:

| Category | Base type | Handling |
|---|---|---|
| Programming errors | built-ins (`ValueError`, `TypeError`) | Not caught; they crash and get fixed |
| Contract violations | `RegistryError` | Caught at the composition root; fail startup loudly |
| Operational errors | `TelemetryError` | Caught by `services`, surfaced to the user as an event |

Rules:

- Each layer translates foreign exceptions into its own taxonomy at its
  boundary. A `csv.Error` never reaches `ui`.
- A single failing source or provider must not crash the shell.
- `__cause__` is always preserved when wrapping.

---

## 7. Cancellation

- Every long-running operation accepts a cancellation token and returns promptly
  once it is set.
- The token is toolkit-agnostic (`threading.Event`), so services are testable
  without a Qt event loop.
- Cancellation is cooperative: workers check between units of work, at a
  granularity keeping response under roughly 100 ms.
- A cancelled operation still runs cleanup and still emits a terminal event. The
  UI never waits on a result that will not arrive.
- Application shutdown cancels all outstanding work and joins before exit.

---

## 8. Verification

| Acceptance criterion | Verified by |
|---|---|
| Layers and allowed dependencies documented | This document |
| Registries have typed contracts and deterministic failures | `tests/unit/test_registry.py` |
| CI detects forbidden dependency directions | import-linter contracts in `pyproject.toml`, run in CI |
| A source and widget register without editing the shell | `tests/architecture/test_extension_points.py` |

---

## 9. Decision records

| ADR | Title |
|---|---|
| [0001](adr/0001-layered-architecture.md) | Layered package architecture with enforced dependency direction |
| [0002](adr/0002-registry-placement.md) | Generic registry in `core`, concrete registries in the owning layer |
| [0003](adr/0003-immutable-cross-thread-events.md) | Immutable events across the thread boundary, cooperative cancellation |