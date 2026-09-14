# Completed Issues

This file records the completed work for the LBR dashboard rebuild.

## P0 Issue #16 — Desktop application foundation

Issue: https://github.com/longhorn-baja-racing/lbr-dashboard/issues/16

### What changed

- Migrated the prototype into the installable `lbr_dashboard` package.
- Replaced PyQt6 with PySide6.
- Replaced Matplotlib with PyQtGraph.
- Added the `lbr-dashboard` command-line entry point and module entry point.
- Added packaging configuration and dependency management with `pyproject.toml`
  and `uv.lock`.
- Kept compatibility wrappers in the original `src/` locations.
- Added tests, documentation, and updated development commands.

### Plotting fixes

- Automatically select and plot the first signal after loading a CSV.
- Reset the plot range when switching signals.
- Normalize timestamp data so plotted time starts at `0`.
- Use the label `Time since start (ms)` instead of allowing negative elapsed
  time on the graph.

### Result

The desktop dashboard can launch, open the sample CSV, display its columns,
and plot numeric data.

## P0 Issue #17 — Architecture boundaries and internal registries

Issue: https://github.com/longhorn-baja-racing/lbr-dashboard/issues/17

### What changed

- Added framework-neutral typed contracts for telemetry sources, importers,
  widgets, unit converters, and analysis providers.
- Added application-owned registries instead of global service locators or
  singletons.
- Added deterministic registry ordering.
- Added clear failures for duplicate IDs, unknown IDs, and factory errors.
- Added cooperative cancellation for background work.
- Added immutable worker events queued for the owning/UI thread.
- Added lifecycle cleanup and error reporting for background services.
- Allowed the application shell to receive a registry bundle so new sources and
  widgets can be registered without editing the shell.
- Added architecture documentation and ADR 0001.
- Added static tests that reject forbidden dependency directions.

### CI fix

The first GitHub Actions run failed on Ubuntu because PySide6 could not find
`libEGL.so.1`. The workflow was updated to:

- install the Linux package `libegl1`;
- set `QT_QPA_PLATFORM=offscreen` for headless Qt testing.

The updated workflow passed successfully.

## P0 Issue #18 — Schema-driven signal model and hierarchical signal registry

Issue: https://github.com/longhorn-baja-racing/lbr-dashboard/issues/18

### What changed

- Added immutable, typed `SignalDescriptor` metadata for stable IDs, display
  names, hierarchy paths, signal types, shapes, canonical units, source/device
  IDs, nominal rates, descriptions, calibration, display metadata, and
  explicit availability.
- Added versioned `SignalSchema` serialization with round-trip support.
- Preserved unknown schema and descriptor fields for forward compatibility,
  while also supporting strict rejection when requested.
- Added sparse `SignalSeries` and `SignalSample` storage so signals with
  different sample rates do not require synthetic duplicate rows.
- Added deterministic hierarchy lookup and token-based search through
  `SignalRegistry`.
- Allowed unknown future signal types to remain inspectable without creating a
  closed vehicle-subsystem enum.
- Added current BNO055-style descriptors and a future suspension descriptor in
  the mixed-rate fixture.

### Validation

- 37 tests passed, including schema round trips, identifier/type/shape/unit
  validation, unknown-field handling, sparse mixed-rate samples, and
  deterministic hierarchy/search behavior.
- Ruff formatting and linting passed.
- Pyright passed with 0 errors and 0 warnings.

Issue #18 is currently uncommitted and unpushed on local branch
`codex/p0-18-signal-model`. No PR was created for this issue.

## Validation

- 13 tests passed locally.
- Ruff formatting passed.
- Ruff linting passed.
- Pyright passed with 0 errors and 0 warnings.
- GitHub Actions push and pull-request checks passed.

## GitHub status

- PR: https://github.com/longhorn-baja-racing/lbr-dashboard/pull/96
- PR target: `develop`
- Feature branch: `codex/p0-17-architecture-boundaries`
- Implementation commit: `fb71e8b`
- CI fix commit: `e0e8910`
- `develop` was not directly committed to or pushed to.
