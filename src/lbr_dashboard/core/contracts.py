"""Typed extension contracts shared by the dashboard layers.

These protocols intentionally contain no Qt types.  Concrete providers can be
implemented by later milestones without making the domain depend on the UI.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Condition
from time import monotonic
from typing import Any, Protocol, TypeAlias

from .lifecycle import CancellationToken, ServiceEvent
from .signals import SignalDescriptor, SignalSample, SignalSeries

Session: TypeAlias = Any
TelemetrySourceFactory: TypeAlias = Callable[..., "TelemetrySource"]
ImporterFactory: TypeAlias = Callable[..., "Importer"]
WidgetFactoryCallable: TypeAlias = Callable[..., "WidgetFactory"]
UnitConverterFactory: TypeAlias = Callable[..., "UnitConverter"]
AnalysisProviderFactory: TypeAlias = Callable[..., "AnalysisProvider"]
EventSink: TypeAlias = Callable[[ServiceEvent], None]
SourceEventSink: TypeAlias = Callable[["SourceEvent"], None]


class SourceState(str, Enum):
    """Lifecycle states shared by replay, live, and simulated sources."""

    CREATED = "created"
    OPEN = "open"
    RUNNING = "running"
    ENDED = "ended"
    STOPPED = "stopped"
    FAILED = "failed"


class UnsupportedSourceOperation(RuntimeError):
    """Raised when a caller requests an operation a source does not support."""


class SourceEventKind(str, Enum):
    """Normalized events a source can deliver to downstream consumers."""

    DESCRIPTOR = "descriptor"
    RECORD = "record"
    HEALTH = "health"
    ERROR = "error"
    END_OF_STREAM = "end_of_stream"


@dataclass(frozen=True, slots=True)
class SourceCapabilities:
    """Truthful source capabilities; unsupported controls must not be implied."""

    is_live: bool
    supports_seek: bool
    supports_rate_control: bool
    buffer_capacity: int

    def __post_init__(self) -> None:
        if not isinstance(self.is_live, bool):
            raise TypeError("is_live must be a boolean")
        if not isinstance(self.supports_seek, bool):
            raise TypeError("supports_seek must be a boolean")
        if not isinstance(self.supports_rate_control, bool):
            raise TypeError("supports_rate_control must be a boolean")
        if (
            isinstance(self.buffer_capacity, bool)
            or not isinstance(self.buffer_capacity, int)
            or self.buffer_capacity <= 0
        ):
            raise ValueError("buffer_capacity must be a positive integer")


@dataclass(frozen=True, slots=True)
class SourceError:
    """Observable source failure context safe to cross a thread boundary."""

    code: str
    message: str
    recoverable: bool = False
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("source error code must not be empty")
        if not self.message.strip():
            raise ValueError("source error message must not be empty")
        if not isinstance(self.recoverable, bool):
            raise TypeError("recoverable must be a boolean")


@dataclass(frozen=True, slots=True)
class SourceHealth:
    """Point-in-time health and loss metrics for a source."""

    state: SourceState
    buffered_records: int = 0
    dropped_records: int = 0
    last_error: SourceError | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("buffered_records", self.buffered_records),
            ("dropped_records", self.dropped_records),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class SourceEvent:
    """A typed source event; records always pair a stable ID with their sample."""

    kind: SourceEventKind
    descriptor: SignalDescriptor | None = None
    signal_id: str | None = None
    sample: SignalSample | None = None
    health: SourceHealth | None = None
    error: SourceError | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SourceEventKind):
            raise TypeError("kind must be a SourceEventKind")
        payloads = (self.descriptor, self.sample, self.health, self.error, self.reason)
        expected = {
            SourceEventKind.DESCRIPTOR: self.descriptor,
            SourceEventKind.RECORD: self.sample,
            SourceEventKind.HEALTH: self.health,
            SourceEventKind.ERROR: self.error,
            SourceEventKind.END_OF_STREAM: self.reason,
        }[self.kind]
        if expected is None or sum(value is not None for value in payloads) != 1:
            raise ValueError(f"{self.kind.value} events must contain exactly one matching payload")
        if self.kind is SourceEventKind.RECORD:
            if not isinstance(self.signal_id, str) or not self.signal_id:
                raise ValueError("record events require a signal_id")
            SignalSeries.from_samples(self.signal_id, ())
        elif self.signal_id is not None:
            raise ValueError("signal_id is only valid for record events")


@dataclass(frozen=True, slots=True)
class SourceQueueStats:
    """Metrics for a bounded event queue."""

    capacity: int
    buffered: int
    published: int
    dropped: int


class SourceEventQueue:
    """Bounded, thread-safe handoff from a source worker to its owner.

    Data events are bounded by ``capacity``. When full, data events are either
    dropped or wait up to ``timeout``. Descriptor, error, and end-of-stream
    control events are never dropped: they evict the oldest data event, then
    wait for capacity if the queue contains only control events.
    """

    def __init__(self, capacity: int) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._queue: deque[SourceEvent] = deque()
        self._capacity = capacity
        self._published = 0
        self._dropped = 0
        self._condition = Condition()

    def publish(self, event: SourceEvent, *, timeout: float = 0.0) -> bool:
        """Publish data with optional backpressure; control events wait for space."""

        if timeout < 0:
            raise ValueError("timeout must not be negative")
        deadline = monotonic() + timeout
        critical = event.kind in {
            SourceEventKind.DESCRIPTOR,
            SourceEventKind.ERROR,
            SourceEventKind.END_OF_STREAM,
        }
        with self._condition:
            while len(self._queue) >= self._capacity:
                if critical:
                    for index, buffered in enumerate(self._queue):
                        if buffered.kind in (SourceEventKind.RECORD, SourceEventKind.HEALTH):
                            del self._queue[index]
                            self._dropped += 1
                            break
                    else:
                        # Keep the queue bounded and preserve every control event.
                        self._condition.wait()
                        continue
                    break
                if timeout == 0:
                    self._dropped += 1
                    return False
                remaining = deadline - monotonic()
                if remaining <= 0:
                    self._dropped += 1
                    return False
                self._condition.wait(remaining)
            self._queue.append(event)
            self._published += 1
            self._condition.notify_all()
        return True

    def drain(self, limit: int | None = None) -> tuple[SourceEvent, ...]:
        """Drain at most ``limit`` events, or all currently buffered events."""

        if limit is not None and (isinstance(limit, bool) or limit < 0):
            raise ValueError("limit must be non-negative or None")
        with self._condition:
            count = len(self._queue) if limit is None else min(limit, len(self._queue))
            events = tuple(self._queue.popleft() for _ in range(count))
            self._condition.notify_all()
            return events

    @property
    def stats(self) -> SourceQueueStats:
        with self._condition:
            return SourceQueueStats(
                self._capacity,
                len(self._queue),
                self._published,
                self._dropped,
            )


class TelemetrySource(Protocol):
    """Source of replayed, live, or simulated telemetry, independent of Qt.

    ``start`` is the blocking producer operation and is intended to run inside
    a :class:`BackgroundService`.  It emits normalized descriptor/record/
    health/error/end events to an owner-controlled sink. ``open`` and ``close``
    are repeatable lifecycle boundaries; ``stop`` must unblock ``start``.
    Cancellation stops production, while a start failure must transition to
    ``FAILED`` and remain observable through an error event and health state.
    """

    @property
    def source_id(self) -> str: ...

    @property
    def capabilities(self) -> SourceCapabilities: ...

    @property
    def state(self) -> SourceState: ...

    def open(self) -> None: ...

    def start(self, events: SourceEventSink, cancellation: CancellationToken) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...

    def seek(self, timestamp_ns: int) -> None: ...

    def set_rate(self, rate_hz: float) -> None: ...

    def health(self) -> SourceHealth: ...


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
