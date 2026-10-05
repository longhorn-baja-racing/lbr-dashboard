# Dashboard architecture

This document is the dependency contract for the from-scratch dashboard
rebuild. It is intentionally small until the later telemetry milestones add
concrete providers.

## Layers and allowed dependencies

| Layer | Responsibility | May depend on |
| --- | --- | --- |
| `core` | Typed protocols, registries, immutable events, cancellation, and lifecycle primitives | Python standard library |
| `sources` | Live/replay telemetry source adapters | `core` |
| `importers` | File and stream importers | `core` |
| `units` | Unit-conversion providers | `core` |
| `analysis` | Analysis providers | `core` and normalized model contracts |
| `ui` | Qt widgets and presentation state | `core`, Qt, and PyQtGraph |
| `app` | Composition root and process lifecycle | every production layer |

The current repository has the `core`, `importers`, `ui`, and `app` layers.
Other provider layers are reserved for later milestones; the UI receives
importer-produced models through core contracts and does not import provider
implementations.

Forbidden directions enforced by the architecture tests:

- `core` may not import `app`, `ui`, `sources`, `importers`, `units`, or
  `analysis`.
- Provider layers may not import `app` or `ui`.
- `ui` may not import concrete provider layers.

## Ownership and boundaries

- `app.main` owns the process-level `QApplication` and creates one
  application-owned `RegistryBundle` for each shell instance.
- `RegistryBundle` is passed through composition. It is not a global singleton
  and it does not contain business logic.
- Registries are internal extension mechanisms. IDs are stable within one
  application instance, padded identifiers are rejected, duplicate
  registration fails immediately, and unknown IDs fail with a descriptive
  `KeyError`.
- Importers own file decoding and normalized log data. UI widgets render the
  resulting `LogSession` and do not parse CSV or maintain parallel log arrays.
- Factory exceptions are wrapped as `FactoryError` with the registry and ID so
  the composition boundary can report them consistently.
- A source/importer/analysis provider owns its own resources. The application
  owner is responsible for calling `stop` or cancelling its worker before the
  owner is destroyed.
- Worker code never calls Qt widgets. It publishes immutable `ServiceEvent`
  values to a queue; the owning/UI thread drains that queue at its normal
  update boundary.
- Cancellation is cooperative. Long-running work must check its
  `CancellationToken` and release resources in `finally` blocks.

## Registration example

```python
from lbr_dashboard.core import RegistryBundle

registries = RegistryBundle()
registries.telemetry_sources.register("demo", DemoSource)
registries.widgets.register("demo_plot", DemoWidget)
window = create_main_window(registries)
```

The shell does not need to be edited when either provider is added.
