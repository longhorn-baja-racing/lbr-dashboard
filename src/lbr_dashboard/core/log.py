"""Presentation-independent imported tabular log data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol, TypeAlias

NumericColumn: TypeAlias = tuple[float | None, ...]


@dataclass(frozen=True, slots=True)
class LogSession:
    """Immutable rows and pre-parsed numeric columns shared with presenters."""

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    numeric_columns: Mapping[str, NumericColumn]

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", tuple(self.headers))
        object.__setattr__(self, "rows", tuple(tuple(row) for row in self.rows))
        object.__setattr__(
            self,
            "numeric_columns",
            MappingProxyType(
                {name: tuple(values) for name, values in self.numeric_columns.items()}
            ),
        )

    def numeric_column(self, name: str) -> NumericColumn | None:
        """Return the parsed values for one column, when that column exists."""

        return self.numeric_columns.get(name)

    @classmethod
    def from_rows(cls, headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> LogSession:
        """Create normalized rows and numeric columns from decoded values."""

        def as_float(value: str) -> float | None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        columns = {
            header: tuple(as_float(row[index]) if index < len(row) else None for row in rows)
            for index, header in enumerate(headers)
        }
        return cls(headers, rows, columns)


class LogImporter(Protocol):
    """Decode a file into the normalized, presentation-independent log model."""

    def import_session(self, path: Path) -> LogSession: ...
