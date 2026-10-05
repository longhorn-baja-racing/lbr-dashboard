"""Presentation-independent imported tabular log data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias

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
        object.__setattr__(self, "numeric_columns", MappingProxyType(dict(self.numeric_columns)))

    def numeric_column(self, name: str) -> NumericColumn | None:
        return self.numeric_columns.get(name)

    @classmethod
    def from_rows(cls, headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> LogSession:
        """Create a normalized session from decoded tabular rows."""

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
