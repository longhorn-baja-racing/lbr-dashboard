"""Backward-compatible wrapper; use ``python -m lbr_dashboard`` instead."""

from lbr_dashboard.app import main

if __name__ == "__main__":
    raise SystemExit(main())
