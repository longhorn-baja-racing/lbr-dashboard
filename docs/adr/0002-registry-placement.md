# ADR-0002: Generic registry in `core`, concrete registries in the owning layer

## Status

Proposed, pending review on #17

## Context

The scope for #17 asks for registries covering telemetry sources, importers,
widgets, unit conversions, and analysis providers. It also states that core
modules expose typed protocols or ABCs, **not Qt widgets**.

These pull against each other. A widget registry stores widget factories, which
are Qt types. If every registry lives in `core`, then `core` either imports
PySide6 (violating ADR-0001's most important contract) or types the widget
registry as `Registry[Any]`, which discards the type safety that motivated
having a registry at all.

A further constraint from the issue: no business logic in service locators, and
no global singletons. So a single module-level `REGISTRIES` dict is out.

## Decision

Split the machinery from the instances.

**The generic `Registry[T]` lives in `core.registry`.** It is type-parameterised
and knows nothing about what it stores. Registration, lookup, ordering, and
failure behaviour are the same regardless of the contained type. It imports only
the stdlib.

**Concrete registry instances live in the layer that owns the registered type:**

| Registry | Defined in | Registers |
|---|---|---|
| Source registry | `sources` | `TelemetrySource` factories |
| Importer registry | `sources` | Log format importers |
| Analysis registry | `services` | `AnalysisProvider` factories |
| Widget registry | `ui` | Widget factories |
| Unit conversion registry | `core` | Pure conversion functions |

`WidgetRegistry = FactoryRegistry[QWidget]` is therefore declared in `ui`, where
importing Qt is expected, and `core` never sees a widget type.

**Registries are constructed in `app` and passed explicitly** to the components
that need them. They are not module-level globals and are not reachable through
a locator.

## Alternatives considered

**One registry-of-registries in `core`.** A single lookup point, but it is a
service locator by another name: any module can reach any extension point, which
makes the dependency graph unanalysable and defeats ADR-0001's contracts.
Explicitly out of scope per the issue.

**Decorator-based registration** (`@register_source("csv")` at module scope).
Ergonomic, and common in plugin systems. Rejected because registration then
happens as an import side effect: what is registered depends on what has been
imported, which varies by entry point and by test. It also makes the populated
set invisible. There is no single place to read off what the application
contains.

**Module-level singleton instances with a `reset()` for tests.** Rejected: every
test must remember to call it, and the one that forgets produces a failure in a
different test file.

## Consequences

- `core` stays free of Qt, so the registry has unit tests that run headless with no event loop.
- Each layer owns its own extension point, and the type parameter is meaningful at every use site.
- Every test constructs a fresh registry. There is no shared state and no teardown, so tests cannot leak into each other.
- The full set of registered entries is visible in one function in `app`.
- Cost: registry instances are scattered across four modules rather than centralised, so "what registries exist?" is answered by this table rather than by one file.
- Cost: `app` must import from every layer to populate the registries, and every component that needs a registry must be handed one. This is more plumbing than a global, and it is the price of the two properties above.