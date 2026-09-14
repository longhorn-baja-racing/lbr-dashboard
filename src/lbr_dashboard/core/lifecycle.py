"""Cancellation and worker lifecycle primitives shared by adapters and UI."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Any, TypeAlias


class CancellationRequested(Exception):
    """Raised by cooperative work after its owner requests cancellation."""


class CancellationToken:
    """Thread-safe, cooperative cancellation signal."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise CancellationRequested("Background work was cancelled")


@dataclass(frozen=True)
class ServiceEvent:
    """Immutable event queued by worker code for consumption by its owner."""

    kind: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class ServiceFailure:
    """Serializable worker failure context safe to hand across a thread boundary."""

    exception_type: str
    message: str


Work: TypeAlias = Callable[[CancellationToken, Callable[[ServiceEvent], None]], None]


class BackgroundService:
    """Own one worker thread and expose queued events, cancellation, and cleanup.

    The service never invokes a UI callback from the worker.  Work puts
    immutable events into the service queue; the owning thread calls
    :meth:`drain_events` at its normal update boundary.
    """

    def __init__(self, work: Work) -> None:
        self._work = work
        self._cancel = CancellationToken()
        self._events: list[ServiceEvent] = []
        self._lock = Lock()
        self._thread: Thread | None = None
        self._failure: ServiceFailure | None = None
        self._finished = Event()

    def start(self) -> None:
        """Start the service once."""

        with self._lock:
            if self._thread is not None:
                raise RuntimeError("Background service has already been started")
            self._thread = Thread(target=self._run, name="lbr-dashboard-worker", daemon=True)
            self._thread.start()

    def cancel(self) -> None:
        """Request cooperative cancellation."""

        self._cancel.cancel()

    def join(self, timeout: float | None = None) -> bool:
        """Wait for cleanup and return whether the worker finished."""

        if self._thread is None:
            return True
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def drain_events(self) -> tuple[ServiceEvent, ...]:
        """Return and clear events; call this from the owning/application thread."""

        with self._lock:
            events = tuple(self._events)
            self._events.clear()
            return events

    @property
    def failure(self) -> ServiceFailure | None:
        return self._failure

    @property
    def is_finished(self) -> bool:
        return self._finished.is_set()

    def _emit(self, event: ServiceEvent) -> None:
        with self._lock:
            self._events.append(event)

    def _run(self) -> None:
        try:
            self._work(self._cancel, self._emit)
        except CancellationRequested:
            pass
        except Exception as exc:
            self._failure = ServiceFailure(type(exc).__name__, str(exc))
        finally:
            self._finished.set()
