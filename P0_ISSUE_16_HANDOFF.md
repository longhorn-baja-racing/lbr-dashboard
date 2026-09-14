# P0 Issues #16 and #17 Handoff

## Issue

**[P0] Rebuild the desktop application foundation with PySide6 and PyQtGraph**

- Issue: https://github.com/longhorn-baja-racing/lbr-dashboard/issues/16
- Repository: https://github.com/longhorn-baja-racing/lbr-dashboard
- Requested pull-request target: `main`
- Current GitHub default branch: `develop`

## What was implemented

The dashboard foundation was migrated from the original prototype into a named,
installable Python package.

- Replaced PyQt6 with PySide6.
- Replaced Matplotlib with PyQtGraph.
- Added the `src/lbr_dashboard` package.
- Added `pyproject.toml` with runtime and development dependencies.
- Added `uv.lock` with resolved dependencies.
- Added the supported `lbr-dashboard` command-line entry point.
- Added the `python -m lbr_dashboard` entry point.
- Added a canonical version source in `src/lbr_dashboard/version.py`.
- Added package resource helpers in `src/lbr_dashboard/resources.py`.
- Migrated the main window, panels, menu bar, and plotting code into the package.
- Left compatibility wrappers in the original `src/` locations.
- Updated the README and Makefile for the new workflow.

## Plotting fix added during manual testing

The first loaded signal did not automatically plot because the list widget did
not have an active selection after loading. This was fixed by selecting and
plotting the first column after CSV load.

The plot now also:

- resets its automatic view range when changing signals;
- labels the horizontal axis `Time since start (ms)`;
- normalizes timestamps so plotted time starts at `0`, even if source timestamps
  are negative.

## Validation completed

From the dashboard repository directory:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv lock --check
```

Issue #16 results:

- 4 tests passed.
- Ruff formatting passed.
- Ruff linting passed.
- Pyright reported 0 errors.
- `uv lock --check` passed.
- The desktop app launched successfully and was manually tested with the sample
  CSV file.

## P0 Issue #17 implementation

**[P0] Define and enforce architectural boundaries and internal registries**

- Issue: https://github.com/longhorn-baja-racing/lbr-dashboard/issues/17
- Local branch: `codex/p0-17-architecture-boundaries`
- Base: `develop` at the existing PySide6/PyQtGraph foundation

The next prioritized open P0 issue was #17. The local implementation adds:

- `lbr_dashboard.core` contracts with typed protocols for sources, importers,
  widgets, unit converters, and analysis providers;
- an application-owned `RegistryBundle` with deterministic identifier order,
  duplicate-ID rejection, unknown-ID errors, and contextual factory failures;
- cooperative cancellation, immutable worker events, and owned background
  service cleanup without calling Qt from worker code;
- dependency-boundary checks that reject documented forbidden imports;
- architecture and registry/lifecycle tests, including registration of a
  minimal source and widget without editing the shell;
- `docs/ARCHITECTURE.md` and ADR 0001 documenting responsibilities,
  ownership, lifecycle, cancellation, and thread boundaries;
- GitHub Actions quality workflow running tests, linting, formatting, and type
  checks.

Issue #17 validation results:

- 13 tests passed.
- Ruff formatting passed.
- Ruff linting passed.
- Pyright reported 0 errors and 0 warnings.
- The existing UI smoke tests continue to pass.

## GitHub status

Issue #16 was previously committed as `9956bd0` and merged into the remote
`develop` branch by merge commit `271c316`. Issue #17 is committed locally as
`c4640fe` on `codex/p0-17-architecture-boundaries`, but it has not been pushed
and no pull request has been created. The remote `develop` branch has not been
changed by this issue #17 work.

The earlier issue #16 workflow was:

1. Create the feature branch `codex/p0-16-dashboard-foundation` from `main`.
2. Commit the P0 #16 changes to that feature branch only.
3. Push only the feature branch.
4. Open a pull request from `codex/p0-16-dashboard-foundation` into `main`.
5. Leave the pull request open for human review; do not merge it automatically.

`main` must not be committed to or pushed to directly. For issue #17, the
working base is `develop`, the repository's current default branch.

## GitHub connection status

The previously detected GitHub connector account was `premetl9-ui`, which had
read-only access to this repository. That GitHub app connection was removed so
the intended `SaiVeerapaneni` account can be connected later if a PR is needed.

To connect the correct account in Codex:

1. Open **Codex Settings**.
2. Open **Apps** or **Connectors**.
3. Disconnect the current GitHub connection if it shows `premetl9-ui`.
4. Select **Connect** for GitHub.
5. Sign in to GitHub as `SaiVeerapaneni`.
6. Authorize access to the `longhorn-baja-racing` organization and
   `lbr-dashboard` repository.
7. Return to Codex and reply that the account is ready.

The connection guide is available here:

https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt-deep-research

After the correct account is connected, verify that it has permission to create
branches and push to `longhorn-baja-racing/lbr-dashboard`. Then the feature
branch and review PR can be created without touching `main`.

## Out of scope for this PR

This work does not yet implement the later P0 issues for:

- schema-driven signals (#18);
- telemetry protocol (#19);
- telemetry sources and sessions (#20–#21);
- replay/live clock (#22);
- simulator (#23);
- configuration, diagnostics, CI, or performance infrastructure (#24–#27).
