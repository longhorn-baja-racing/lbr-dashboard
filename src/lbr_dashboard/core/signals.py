"""Schema-driven signal descriptors, sparse samples, and signal registry."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any, TypeAlias

from .registry import RegistryError

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]
SchemaVersion: TypeAlias = int | str

KNOWN_SIGNAL_TYPES = frozenset({"numeric", "boolean", "string", "event", "vector", "status"})
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_PATH_SEGMENT = re.compile(r"^[a-z][a-z0-9_-]*$")
_TOKEN = re.compile(r"[a-z0-9]+")


class SignalSchemaError(ValueError):
    """Raised when a signal descriptor or schema is invalid."""


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SignalSchemaError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_identifier(value: object, field_name: str) -> str:
    identifier = _require_text(value, field_name)
    if _IDENTIFIER.fullmatch(identifier) is None:
        raise SignalSchemaError(
            f"{field_name} '{identifier}' must use lowercase dot, dash, or underscore segments"
        )
    return identifier


def _validate_path(value: object) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or not value:
        raise SignalSchemaError("path must be a non-empty sequence of segments")
    path = tuple(_require_text(segment, "path segment") for segment in value)
    invalid = [segment for segment in path if _PATH_SEGMENT.fullmatch(segment) is None]
    if invalid:
        raise SignalSchemaError(f"path segments are invalid: {invalid}")
    return path


def _validate_shape(value: object) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SignalSchemaError("shape must be a sequence of positive integers")
    shape: list[int] = []
    for dimension in value:
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension <= 0:
            raise SignalSchemaError("shape dimensions must be positive integers")
        shape.append(dimension)
    return tuple(shape)


def _freeze_json(value: object, field_name: str) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, float) and not isfinite(value):
            raise SignalSchemaError(f"{field_name} cannot contain non-finite numbers")
        return value
    if isinstance(value, Mapping):
        frozen = {
            _require_text(key, f"{field_name} key"): _freeze_json(item, f"{field_name}.{key}")
            for key, item in value.items()
        }
        return MappingProxyType(frozen)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(_freeze_json(item, field_name) for item in value)
    raise SignalSchemaError(f"{field_name} contains unsupported value {type(value).__name__}")


def _thaw_json(value: JsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in sorted(value.items())}
    if isinstance(value, tuple):
        return tuple(_thaw_json(item) for item in value)
    return value


def _freeze_mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, JsonValue]:
    frozen = _freeze_json(value, field_name)
    if not isinstance(frozen, Mapping):
        raise SignalSchemaError(f"{field_name} must be an object")
    return frozen


def _mapping_to_dict(value: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    return {key: _thaw_json(item) for key, item in sorted(value.items())}


@dataclass(frozen=True, slots=True)
class SignalAvailability:
    """Explicit availability metadata; missing data is never represented as zero."""

    available: bool = True
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.available, bool):
            raise SignalSchemaError("availability.available must be a boolean")
        if self.reason is not None:
            reason = _require_text(self.reason, "availability.reason")
            object.__setattr__(self, "reason", reason)
        if not self.available and self.reason is None:
            raise SignalSchemaError("unavailable signals require availability.reason")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"available": self.available, "reason": self.reason}

    @classmethod
    def from_dict(cls, value: object) -> SignalAvailability:
        if not isinstance(value, Mapping):
            raise SignalSchemaError("availability must be an object")
        unknown = set(value) - {"available", "reason"}
        if unknown:
            raise SignalSchemaError(f"unknown availability fields: {sorted(unknown)}")
        return cls(available=value.get("available", True), reason=value.get("reason"))


@dataclass(frozen=True, slots=True)
class SignalDescriptor:
    """Immutable metadata describing one signal independently of its samples."""

    identifier: str
    display_name: str
    path: tuple[str, ...]
    data_type: str
    source_id: str
    shape: tuple[int, ...] = ()
    canonical_unit: str | None = None
    device_id: str | None = None
    nominal_rate_hz: float | None = None
    description: str = ""
    availability: SignalAvailability = field(default_factory=SignalAvailability)
    calibration: Mapping[str, JsonValue] = field(default_factory=dict)
    display: Mapping[str, JsonValue] = field(default_factory=dict)
    extra: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "identifier", _validate_identifier(self.identifier, "identifier"))
        object.__setattr__(self, "display_name", _require_text(self.display_name, "display_name"))
        object.__setattr__(self, "path", _validate_path(self.path))
        object.__setattr__(self, "data_type", _validate_identifier(self.data_type, "type"))
        object.__setattr__(self, "source_id", _validate_identifier(self.source_id, "source_id"))
        object.__setattr__(self, "shape", _validate_shape(self.shape))

        if self.canonical_unit is not None:
            unit = _require_text(self.canonical_unit, "canonical_unit")
            if any(character.isspace() for character in unit):
                raise SignalSchemaError("canonical_unit must not contain whitespace")
            object.__setattr__(self, "canonical_unit", unit)
        if self.device_id is not None:
            object.__setattr__(self, "device_id", _validate_identifier(self.device_id, "device_id"))
        if self.nominal_rate_hz is not None:
            if not isinstance(self.nominal_rate_hz, (int, float)) or isinstance(
                self.nominal_rate_hz, bool
            ):
                raise SignalSchemaError("nominal_rate_hz must be a positive finite number")
            if not isfinite(float(self.nominal_rate_hz)) or self.nominal_rate_hz <= 0:
                raise SignalSchemaError("nominal_rate_hz must be a positive finite number")
            object.__setattr__(self, "nominal_rate_hz", float(self.nominal_rate_hz))
        if not isinstance(self.description, str):
            raise SignalSchemaError("description must be a string")
        if not isinstance(self.availability, SignalAvailability):
            raise SignalSchemaError("availability must be SignalAvailability")

        object.__setattr__(self, "calibration", _freeze_mapping(self.calibration, "calibration"))
        object.__setattr__(self, "display", _freeze_mapping(self.display, "display"))
        object.__setattr__(self, "extra", _freeze_mapping(self.extra, "extra"))

    @property
    def is_known_type(self) -> bool:
        """Whether this descriptor uses one of the currently known data types."""

        return self.data_type in KNOWN_SIGNAL_TYPES

    @property
    def search_tokens(self) -> tuple[str, ...]:
        """Derive deterministic search metadata from descriptor fields."""

        text = " ".join(
            (
                self.identifier,
                self.display_name,
                *self.path,
                self.data_type,
                self.source_id,
                self.device_id or "",
                self.canonical_unit or "",
                self.description,
            )
        ).lower()
        return tuple(sorted(set(_TOKEN.findall(text))))

    @property
    def unknown_fields(self) -> Mapping[str, JsonValue]:
        """Return forward-compatible fields that were not understood by this version."""

        return self.extra

    def to_dict(self) -> dict[str, JsonValue]:
        result = _mapping_to_dict(self.extra)
        result.update(
            {
                "availability": self.availability.to_dict(),
                "calibration": _mapping_to_dict(self.calibration),
                "canonical_unit": self.canonical_unit,
                "device_id": self.device_id,
                "display": _mapping_to_dict(self.display),
                "display_name": self.display_name,
                "id": self.identifier,
                "nominal_rate_hz": self.nominal_rate_hz,
                "path": self.path,
                "shape": self.shape,
                "source_id": self.source_id,
                "type": self.data_type,
            }
        )
        if self.description:
            result["description"] = self.description
        return result

    @classmethod
    def from_dict(cls, value: object, *, allow_unknown: bool = True) -> SignalDescriptor:
        if not isinstance(value, Mapping):
            raise SignalSchemaError("signal descriptor must be an object")
        known = {
            "availability",
            "calibration",
            "canonical_unit",
            "device_id",
            "display",
            "display_name",
            "description",
            "id",
            "nominal_rate_hz",
            "path",
            "shape",
            "source_id",
            "type",
        }
        missing = sorted({"id", "display_name", "path", "type", "source_id"} - set(value))
        if missing:
            raise SignalSchemaError(f"signal descriptor is missing fields: {missing}")
        extra = {key: item for key, item in value.items() if key not in known}
        if extra and not allow_unknown:
            raise SignalSchemaError(f"unknown signal fields: {sorted(extra)}")
        calibration = value.get("calibration", {})
        display = value.get("display", {})
        if not isinstance(calibration, Mapping) or not isinstance(display, Mapping):
            raise SignalSchemaError("calibration and display must be objects")
        return cls(
            identifier=value["id"],
            display_name=value["display_name"],
            path=value["path"],
            data_type=value["type"],
            source_id=value["source_id"],
            shape=value.get("shape", ()),
            canonical_unit=value.get("canonical_unit"),
            device_id=value.get("device_id"),
            nominal_rate_hz=value.get("nominal_rate_hz"),
            description=value.get("description", ""),
            availability=SignalAvailability.from_dict(value.get("availability", {})),
            calibration=calibration,
            display=display,
            extra=extra,
        )


@dataclass(frozen=True, slots=True)
class SignalSample:
    """One sparse sample; each signal keeps its own timeline."""

    timestamp_ns: int
    value: object | None
    available: bool = True
    quality: str | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.timestamp_ns, bool)
            or not isinstance(self.timestamp_ns, int)
            or not 0 <= self.timestamp_ns <= 0xFFFFFFFFFFFFFFFF
        ):
            raise SignalSchemaError("sample timestamp_ns must be a non-negative uint64 integer")
        if not isinstance(self.available, bool):
            raise SignalSchemaError("sample available must be a boolean")
        if self.available and self.value is None:
            raise SignalSchemaError("available samples must contain a value")
        if self.quality is not None:
            object.__setattr__(self, "quality", _require_text(self.quality, "sample quality"))


@dataclass(frozen=True, slots=True)
class SignalSeries:
    """Sparse storage for one signal without synthetic row alignment."""

    signal_id: str
    samples: tuple[SignalSample, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_id", _validate_identifier(self.signal_id, "signal_id"))
        object.__setattr__(self, "samples", tuple(self.samples))
        if any(not isinstance(sample, SignalSample) for sample in self.samples):
            raise SignalSchemaError("samples must contain SignalSample values")

    @classmethod
    def from_samples(cls, signal_id: str, samples: Iterable[SignalSample]) -> SignalSeries:
        return cls(signal_id=signal_id, samples=tuple(samples))


@dataclass(frozen=True, slots=True)
class SignalSchema:
    """Versioned collection of descriptors with forward-compatible fields."""

    schema_version: SchemaVersion
    signals: tuple[SignalDescriptor, ...]
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)
    extra: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or not isinstance(self.schema_version, (int, str)):
            raise SignalSchemaError("schema_version must be a non-empty string or positive integer")
        if isinstance(self.schema_version, str) and not self.schema_version.strip():
            raise SignalSchemaError("schema_version must be a non-empty string or positive integer")
        if isinstance(self.schema_version, int) and self.schema_version <= 0:
            raise SignalSchemaError("schema_version must be a non-empty string or positive integer")
        signals = tuple(self.signals)
        if any(not isinstance(signal, SignalDescriptor) for signal in signals):
            raise SignalSchemaError("signals must contain SignalDescriptor values")
        identifiers = [signal.identifier for signal in signals]
        duplicates = sorted(
            {identifier for identifier in identifiers if identifiers.count(identifier) > 1}
        )
        if duplicates:
            raise SignalSchemaError(f"duplicate signal identifiers: {duplicates}")
        object.__setattr__(
            self, "signals", tuple(sorted(signals, key=lambda signal: signal.identifier))
        )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata, "metadata"))
        object.__setattr__(self, "extra", _freeze_mapping(self.extra, "extra"))

    def to_dict(self) -> dict[str, JsonValue]:
        result = _mapping_to_dict(self.extra)
        result.update(
            {
                "metadata": _mapping_to_dict(self.metadata),
                "schema_version": self.schema_version,
                "signals": tuple(signal.to_dict() for signal in self.signals),
            }
        )
        return result

    @classmethod
    def from_dict(cls, value: object, *, allow_unknown: bool = True) -> SignalSchema:
        if not isinstance(value, Mapping):
            raise SignalSchemaError("signal schema must be an object")
        if "schema_version" not in value or "signals" not in value:
            raise SignalSchemaError("signal schema requires schema_version and signals")
        signals = value["signals"]
        if isinstance(signals, (str, bytes)) or not isinstance(signals, Sequence):
            raise SignalSchemaError("signals must be a sequence")
        known = {"metadata", "schema_version", "signals"}
        extra = {key: item for key, item in value.items() if key not in known}
        if extra and not allow_unknown:
            raise SignalSchemaError(f"unknown schema fields: {sorted(extra)}")
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise SignalSchemaError("metadata must be an object")
        return cls(
            schema_version=value["schema_version"],
            signals=tuple(
                SignalDescriptor.from_dict(signal, allow_unknown=allow_unknown)
                for signal in signals
            ),
            metadata=metadata,
            extra=extra,
        )


class SignalRegistry:
    """Deterministic hierarchical registry for immutable signal descriptors."""

    def __init__(self, schema: SignalSchema | None = None) -> None:
        self._signals: dict[str, SignalDescriptor] = {}
        if schema is not None:
            self.register_schema(schema)

    def register(self, descriptor: SignalDescriptor) -> None:
        if descriptor.identifier in self._signals:
            raise RegistryError(
                f"Identifier '{descriptor.identifier}' is already registered in registry 'signals'"
            )
        self._signals[descriptor.identifier] = descriptor

    def register_schema(self, schema: SignalSchema) -> None:
        for descriptor in schema.signals:
            self.register(descriptor)

    def get(self, identifier: str) -> SignalDescriptor:
        try:
            return self._signals[identifier]
        except KeyError as exc:
            raise KeyError(f"Unknown signal identifier '{identifier}'") from exc

    def descriptors(self) -> tuple[SignalDescriptor, ...]:
        return tuple(self._signals[identifier] for identifier in sorted(self._signals))

    def search(self, query: str) -> tuple[SignalDescriptor, ...]:
        tokens = set(_TOKEN.findall(query.lower()))
        if not tokens:
            return self.descriptors()
        return tuple(
            descriptor
            for descriptor in self.descriptors()
            if tokens.issubset(descriptor.search_tokens)
        )

    def under_path(self, path: Sequence[str]) -> tuple[SignalDescriptor, ...]:
        normalized = _validate_path(path)
        return tuple(
            descriptor
            for descriptor in self.descriptors()
            if descriptor.path[: len(normalized)] == normalized
        )

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._signals

    def __len__(self) -> int:
        return len(self._signals)
