# Longhorn Baja Telemetry Dashboard

The dashboard is a Python desktop application for replaying logs and, in later
milestones, displaying live vehicle telemetry. The P0 foundation uses PySide6
for the application shell and PyQtGraph for plotting.

## Supported platforms

- Python 3.10–3.13
- Windows (Tier 1), macOS, and Linux

## Development setup

[uv](https://docs.astral.sh/uv/) is the supported environment and dependency
manager:

```bash
uv sync --extra dev
uv run lbr-dashboard
```

The module entry point is also supported:

```bash
uv run python -m lbr_dashboard
```

For a plain pip environment, install the project in editable mode with
`pip install -e .`.

## Quality checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

The current shell retains the original CSV smoke-test flow through **File →
Open**. Telemetry import, protocol, and session boundaries are implemented in
the next P0 milestones.
