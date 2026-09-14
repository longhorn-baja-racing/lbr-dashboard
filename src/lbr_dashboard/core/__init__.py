"""Framework-neutral contracts and lifecycle primitives for the dashboard."""

from .contracts import (
    AnalysisProvider,
    Importer,
    TelemetrySource,
    UnitConverter,
    WidgetFactory,
)
from .lifecycle import (
    BackgroundService,
    CancellationRequested,
    CancellationToken,
    ServiceEvent,
    ServiceFailure,
)
from .registries import RegistryBundle
from .registry import FactoryError, Registry, RegistryError
from .signals import (
    KNOWN_SIGNAL_TYPES,
    SignalAvailability,
    SignalDescriptor,
    SignalRegistry,
    SignalSample,
    SignalSchema,
    SignalSchemaError,
    SignalSeries,
)

__all__ = [
    "AnalysisProvider",
    "BackgroundService",
    "CancellationRequested",
    "CancellationToken",
    "FactoryError",
    "Importer",
    "Registry",
    "RegistryBundle",
    "RegistryError",
    "KNOWN_SIGNAL_TYPES",
    "SignalAvailability",
    "SignalDescriptor",
    "SignalRegistry",
    "SignalSample",
    "SignalSchema",
    "SignalSchemaError",
    "SignalSeries",
    "ServiceEvent",
    "ServiceFailure",
    "TelemetrySource",
    "UnitConverter",
    "WidgetFactory",
]
