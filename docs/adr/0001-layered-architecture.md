# ADR-0001: Layered package architecture with enforced dependency direction

## Status

Proposed, pending review on #17

## Context

The dashboard is being rebuilt from scratch (#16). The legacy tree offers a
concrete warning about what to avoid:

- The package root is `src/`, which is not usable as an import name.
- `models/constants.py` hard-codes a specific season's sensor set, so adding or
  renaming a signal means editing a module that the UI imports directly.
- UI packages (`left_panel`, `right_panel`, `top_menu_bar`) are organised by
  screen region rather than by responsibility, so there is no layer boundary to
  point at when deciding where new logic belongs.

The rebuild must support arbitrary signals and future transports (live
telemetry, replay, a simulator) without the sensor set or the transport choice
leaking into the UI. Without an explicit dependency direction, the cheapest
place to put new code is always "next to the thing that calls it," which
converges on a single mutually-dependent blob.

Nothing prevents this by convention alone. On a student team with yearly
turnover, an unenforced rule has a shelf life of about one semester.

## Decision

Production code is split into five layers. Dependencies point downward only,
with no cycles:

| Layer | May import | Responsibility |
|---|---|---|
| `core` | stdlib only | Signal model, protocols, registry machinery, errors, unit conversion |
| `sources` | `core` | Log importers, live transports, simulator |
| `services` | `core`, `sources` | Session state, playback clock, analysis, background work |
| `ui` | `core`, `services` | PySide6 widgets, PyQtGraph panels, view models |
| `app` | all | Composition root: builds registries, wires dependencies, starts the shell |

The forbidden directions are declared as import-linter contracts in
`pyproject.toml` and checked in CI. The two that matter most:

- `core` must not import `PySide6` or `PyQtGraph`.
- `ui` must not import `sources`.

The first keeps every contract testable without a GUI toolkit. The second is the
specific coupling most likely to reappear, because reading a transport directly
from a panel is always the shortest path to a working demo.

## Alternatives considered

**Feature-based packages** (`playback/`, `plotting/`, `logging/`, each holding its own model, service, and widget code). Better locality for a single feature, but there is no way to state a dependency rule that a linter can check, every package legitimately contains UI and non-UI code. Rejected because enforceability was the point.

**Two layers (`core` and `ui`).** Simpler, and adequate today. Rejected because the session, clock, and analysis work in #21–#23 has no natural home: it is neither a data contract nor a widget, so it would accumulate in whichever layer was touched last.

**Convention only, no CI enforcement.** Rejected for the turnover reason above.

## Consequences

- A new signal, transport, or panel can be added without editing the shell.
- `core` is testable with plain `pytest`, no Qt event loop and no display.
- Violations fail the PR gate rather than surfacing in review, so the rule survives contributors who have not read this document.
- Cost: more files and more indirection than the current tree. A change that spans a transport and a panel touches three directories rather than one.
- Cost: the layer boundary is occasionally arbitrary, and some code could defensibly live in either `services` or `sources`. The rule is that acquisition belongs in `sources` and anything with a lifetime belongs in `services`.
- The legacy `src/` tree is not migrated into this layout. It is replaced by #16 and deleted.