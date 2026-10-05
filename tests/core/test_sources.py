"""Contract tests for seekable and live TelemetrySource implementations."""

from dataclasses import dataclass
from threading import Event, Thread

import pytest

from lbr_dashboard.core import (
    CancellationRequested,
    CancellationToken,
    SignalDescriptor,
    SignalSample,
    SourceCapabilities,
    SourceError,
    SourceEvent,
    SourceEventKind,
    SourceEventQueue,
    SourceHealth,
    SourceState,
    TelemetrySource,
    UnsupportedSourceOperation,
)

DESCRIPTOR = SignalDescriptor(
    identifier="imu.acceleration.x",
    display_name="Acceleration X",
    path=("vehicle", "imu", "acceleration"),
    data_type="numeric",
    source_id="fake",
    canonical_unit="m/s2",
)


@dataclass
class FakeSource:
    source_id: str
    capabilities: SourceCapabilities
    _state: SourceState = SourceState.CREATED

    @property
    def state(self) -> SourceState:
        return self._state

    def open(self) -> None:
        self._state = SourceState.OPEN

    def start(self, events, cancellation: CancellationToken) -> None:
        if self._state != SourceState.OPEN:
            raise RuntimeError("source must be open before start")
        self._state = SourceState.RUNNING
        try:
            cancellation.raise_if_cancelled()
            events(SourceEvent(SourceEventKind.DESCRIPTOR, descriptor=DESCRIPTOR))
            cancellation.raise_if_cancelled()
            events(
                SourceEvent(
                    SourceEventKind.RECORD,
                    signal_id=DESCRIPTOR.identifier,
                    sample=SignalSample(timestamp_ns=100, value=1.0),
                )
            )
            self._state = SourceState.ENDED
            events(SourceEvent(SourceEventKind.END_OF_STREAM, reason="complete"))
        except CancellationRequested:
            self._state = SourceState.STOPPED
            raise
        except Exception as exc:
            self._state = SourceState.FAILED
            events(
                SourceEvent(
                    SourceEventKind.ERROR,
                    error=SourceError("start_failed", str(exc)),
                )
            )
            raise

    def stop(self) -> None:
        self._state = SourceState.STOPPED

    def close(self) -> None:
        self._state = SourceState.CREATED

    def seek(self, timestamp_ns: int) -> None:
        if not self.capabilities.supports_seek:
            raise UnsupportedSourceOperation("source does not support seek")
        if timestamp_ns < 0:
            raise ValueError("timestamp_ns must not be negative")

    def set_rate(self, rate_hz: float) -> None:
        if not self.capabilities.supports_rate_control:
            raise UnsupportedSourceOperation("source does not support rate control")
        if rate_hz <= 0:
            raise ValueError("rate_hz must be positive")

    def health(self) -> SourceHealth:
        return SourceHealth(self._state)


def run_source(source: TelemetrySource) -> tuple[SourceEvent, ...]:
    """The downstream consumer depends only on the source protocol."""

    received: list[SourceEvent] = []
    source.open()
    source.start(received.append, CancellationToken())
    source.close()
    return tuple(received)


def test_seekable_replay_source_emits_normalized_events_and_closes() -> None:
    source = FakeSource(
        "replay",
        SourceCapabilities(
            is_live=False,
            supports_seek=True,
            supports_rate_control=True,
            buffer_capacity=100,
        ),
    )

    events = run_source(source)

    assert [event.kind for event in events] == [
        SourceEventKind.DESCRIPTOR,
        SourceEventKind.RECORD,
        SourceEventKind.END_OF_STREAM,
    ]
    assert source.state is SourceState.CREATED
    source.seek(100)
    source.set_rate(2.0)


def test_live_source_reports_unsupported_controls_instead_of_lying() -> None:
    source = FakeSource(
        "live",
        SourceCapabilities(
            is_live=True,
            supports_seek=False,
            supports_rate_control=False,
            buffer_capacity=2,
        ),
    )

    with pytest.raises(UnsupportedSourceOperation, match="seek"):
        source.seek(100)
    with pytest.raises(UnsupportedSourceOperation, match="rate control"):
        source.set_rate(2.0)


def test_bounded_queue_makes_overflow_observable() -> None:
    queue = SourceEventQueue(capacity=1)
    first = SourceEvent(
        SourceEventKind.RECORD,
        signal_id=DESCRIPTOR.identifier,
        sample=SignalSample(timestamp_ns=1, value=1.0),
    )
    second = SourceEvent(
        SourceEventKind.RECORD,
        signal_id=DESCRIPTOR.identifier,
        sample=SignalSample(timestamp_ns=2, value=2.0),
    )

    assert queue.publish(first)
    assert not queue.publish(second)
    assert queue.stats.buffered == 1
    assert queue.stats.published == 1
    assert queue.stats.dropped == 1
    assert queue.drain() == (first,)


@pytest.mark.parametrize(
    "event",
    [
        SourceEvent(SourceEventKind.DESCRIPTOR, descriptor=DESCRIPTOR),
        SourceEvent(SourceEventKind.ERROR, error=SourceError("failed", "source failed")),
        SourceEvent(SourceEventKind.END_OF_STREAM, reason="complete"),
    ],
)
def test_critical_events_remain_observable_when_queue_is_full(event: SourceEvent) -> None:
    queue = SourceEventQueue(capacity=1)
    record = SourceEvent(
        SourceEventKind.RECORD,
        signal_id=DESCRIPTOR.identifier,
        sample=SignalSample(timestamp_ns=1, value=1.0),
    )

    assert queue.publish(record)
    assert queue.publish(event)
    assert queue.drain() == (event,)
    assert queue.stats.dropped == 1


def test_control_events_are_retained_when_only_control_events_fill_queue() -> None:
    queue = SourceEventQueue(capacity=1)
    descriptor = SourceEvent(SourceEventKind.DESCRIPTOR, descriptor=DESCRIPTOR)
    error = SourceEvent(SourceEventKind.ERROR, error=SourceError("failed", "source failed"))
    end = SourceEvent(SourceEventKind.END_OF_STREAM, reason="complete")

    assert queue.publish(descriptor)
    started = Event()
    finished = Event()

    def publish_controls() -> None:
        started.set()
        queue.publish(error)
        queue.publish(end)
        finished.set()

    producer = Thread(target=publish_controls)
    producer.start()
    assert started.wait(1.0)
    assert not finished.wait(0.05)
    assert queue.drain() == (descriptor,)
    assert not finished.wait(0.05)
    assert queue.drain() == (error,)
    producer.join(1.0)

    assert finished.is_set()
    assert queue.drain() == (end,)
    assert queue.stats.buffered <= queue.stats.capacity


def test_slow_consumer_can_free_space_for_waiting_publisher() -> None:
    queue = SourceEventQueue(capacity=1)
    first = SourceEvent(
        SourceEventKind.RECORD,
        signal_id=DESCRIPTOR.identifier,
        sample=SignalSample(timestamp_ns=1, value=1.0),
    )
    second = SourceEvent(
        SourceEventKind.RECORD,
        signal_id=DESCRIPTOR.identifier,
        sample=SignalSample(timestamp_ns=2, value=2.0),
    )
    assert queue.publish(first)

    started = Event()
    finished = Event()
    published: list[bool] = []

    def publish_after_wait() -> None:
        started.set()
        published.append(queue.publish(second, timeout=1.0))
        finished.set()

    producer = Thread(target=publish_after_wait)
    producer.start()
    assert started.wait(1.0)
    assert not finished.wait(0.05)
    assert queue.drain() == (first,)
    producer.join(1.0)

    assert finished.is_set()
    assert published == [True]
    assert queue.drain() == (second,)


def test_cancelled_source_start_stops_before_publishing_records() -> None:
    source = FakeSource("replay", SourceCapabilities(False, True, True, 2))
    source.open()
    cancellation = CancellationToken()
    cancellation.cancel()
    received: list[SourceEvent] = []

    with pytest.raises(CancellationRequested):
        source.start(received.append, cancellation)

    assert source.state is SourceState.STOPPED
    assert received == []


def test_cancellation_during_start_stops_before_the_next_record() -> None:
    source = FakeSource("replay", SourceCapabilities(False, True, True, 2))
    source.open()
    cancellation = CancellationToken()
    received: list[SourceEvent] = []

    def receive(event: SourceEvent) -> None:
        received.append(event)
        if event.kind is SourceEventKind.DESCRIPTOR:
            cancellation.cancel()

    with pytest.raises(CancellationRequested):
        source.start(receive, cancellation)

    assert source.state is SourceState.STOPPED
    assert [event.kind for event in received] == [SourceEventKind.DESCRIPTOR]


def test_open_and_close_are_repeatable() -> None:
    source = FakeSource("replay", SourceCapabilities(False, True, True, 2))

    for _ in range(2):
        source.open()
        assert source.state is SourceState.OPEN
        source.close()
        assert source.state is SourceState.CREATED


def test_start_failure_sets_failed_state_and_emits_error() -> None:
    class FailingSource(FakeSource):
        def start(self, events, cancellation: CancellationToken) -> None:
            if self._state is not SourceState.OPEN:
                raise RuntimeError("source must be open before start")
            self._state = SourceState.RUNNING
            try:
                raise OSError("device disconnected")
            except Exception as exc:
                self._state = SourceState.FAILED
                events(
                    SourceEvent(SourceEventKind.ERROR, error=SourceError("start_failed", str(exc)))
                )
                raise

    source = FailingSource("live", SourceCapabilities(True, False, False, 2))
    source.open()
    received: list[SourceEvent] = []

    with pytest.raises(OSError, match="device disconnected"):
        source.start(received.append, CancellationToken())

    assert source.state is SourceState.FAILED
    assert received[0].kind is SourceEventKind.ERROR


def test_source_events_reject_mismatched_or_empty_payloads() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        SourceEvent(SourceEventKind.RECORD)
    with pytest.raises(ValueError, match="signal_id"):
        SourceEvent(
            SourceEventKind.RECORD,
            sample=SignalSample(timestamp_ns=1, value=2),
        )
    with pytest.raises(ValueError, match="exactly one"):
        SourceEvent(
            SourceEventKind.RECORD,
            signal_id=DESCRIPTOR.identifier,
            sample=SignalSample(timestamp_ns=1, value=2),
            health=SourceHealth(SourceState.RUNNING),
        )
