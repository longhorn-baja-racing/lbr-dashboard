"""The application-owned registry bundle.

Keeping these registries together makes the composition root explicit while
avoiding a global service locator.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import (
    AnalysisProvider,
    Importer,
    TelemetrySource,
    UnitConverter,
    WidgetFactory,
)
from .registry import Registry


@dataclass
class RegistryBundle:
    """All internal extension registries owned by one dashboard instance."""

    telemetry_sources: Registry[TelemetrySource] = field(
        default_factory=lambda: Registry("telemetry sources")
    )
    importers: Registry[Importer] = field(default_factory=lambda: Registry("importers"))
    widgets: Registry[WidgetFactory] = field(default_factory=lambda: Registry("widgets"))
    unit_converters: Registry[UnitConverter] = field(
        default_factory=lambda: Registry("unit conversions")
    )
    analysis_providers: Registry[AnalysisProvider] = field(
        default_factory=lambda: Registry("analysis providers")
    )
