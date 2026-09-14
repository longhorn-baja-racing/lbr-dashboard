"""Cancellation, event handoff, and cleanup tests for background services."""

from threading import Event

from lbr_dashboard.core import BackgroundService, CancellationToken, ServiceEvent


def test_background_service_cancels_and_cleans_up() -> None:
    started = Event()
    cleaned_up = Event()

    def work(token: CancellationToken, emit) -> None:
        started.set()
        try:
            while True:
                token.raise_if_cancelled()
        finally:
            cleaned_up.set()

    service = BackgroundService(work)
    service.start()
    assert started.wait(timeout=1)

    service.cancel()

    assert service.join(timeout=1)
    assert cleaned_up.is_set()
    assert service.is_finished
    assert service.failure is None


def test_worker_events_are_queued_until_owner_drains_them() -> None:
    def work(_token: CancellationToken, emit) -> None:
        emit(ServiceEvent("ready", {"count": 1}))

    service = BackgroundService(work)
    service.start()
    assert service.join(timeout=1)

    assert service.drain_events() == (ServiceEvent("ready", {"count": 1}),)
    assert service.drain_events() == ()
