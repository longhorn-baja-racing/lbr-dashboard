"""Typed extension contracts shared by the dashboard layers.

These protocols intentionally contain no Qt types.  Concrete providers can be
implemented by later milestones without making the domain depend on the UI.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, TypeAlias

from .lifecycle import CancellationToken, ServiceEvent

Session: TypeAlias = Any
TelemetrySourceFactory: TypeAlias = Callable[..., "TelemetrySource"]
ImporterFactory: TypeAlias = Callable[..., "Importer"]
WidgetFactoryCallable: TypeAlias = Callable[..., "WidgetFactory"]
UnitConverterFactory: TypeAlias = Callable[..., "UnitConverter"]
AnalysisProviderFactory: TypeAlias = Callable[..., "AnalysisProvider"]
EventSink: TypeAlias = Callable[[ServiceEvent], None]


class TelemetrySource(Protocol):
    """Source of live or replayed telemetry, independent of Qt."""

    @property
    def source_id(self) -> str: ...

    def start(self, events: EventSink, cancellation: CancellationToken) -> None: ...

    def stop(self) -> None: ...


class Importer(Protocol):
    """Importer that turns a file or stream into a normalized session."""

    @property
    def importer_id(self) -> str: ...

    def import_session(self, path: Path) -> Session: ...


class WidgetFactory(Protocol):
    """Factory for a presentation widget without leaking Qt into core."""

    @property
    def widget_id(self) -> str: ...

    def create(self, parent: object | None = None) -> object: ...


class UnitConverter(Protocol):
    """Converter for a named pair of units."""

    @property
    def conversion_id(self) -> str: ...

    def convert(self, values: Sequence[float], metadata: Mapping[str, Any]) -> Sequence[float]: ...


class AnalysisProvider(Protocol):
    """Analysis operation that consumes a normalized session."""

    @property
    def analysis_id(self) -> str: ...

    def analyze(self, session: Session) -> Mapping[str, Any]: ...
