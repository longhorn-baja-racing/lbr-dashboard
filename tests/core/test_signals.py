"""Schema, descriptor, and sparse sample behavior for P0 issue #18."""

import json
from pathlib import Path
from typing import cast

import pytest

from lbr_dashboard.core import (
    SignalDescriptor,
    SignalSample,
    SignalSchema,
    SignalSchemaError,
    SignalSeries,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "signal_schema.json"


def test_schema_round_trips_current_and_future_descriptor_fields() -> None:
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    schema = SignalSchema.from_dict(source)
    round_trip = SignalSchema.from_dict(schema.to_dict())

    assert round_trip.to_dict() == schema.to_dict()
    assert len(round_trip.signals) == 4
    assert "future_calibration_model" in round_trip.signals[1].unknown_fields
    assert round_trip.signals[-1].identifier == "suspension.travel.front_left"


@pytest.mark.parametrize(
    "identifier",
    ["imu.acceleration.x", "power-battery.low", "status_1", "a9"],
)
def test_valid_signal_identifiers_are_accepted(identifier: str) -> None:
    descriptor = SignalDescriptor(
        identifier=identifier,
        display_name="Example",
        path=("vehicle", "example"),
        data_type="future_type",
        source_id="source-01",
    )

    assert descriptor.identifier == identifier
    assert not descriptor.is_known_type


@pytest.mark.parametrize("identifier", ["IMU.x", "imu x", ".imu", "imu..x", ""])
def test_invalid_signal_identifiers_are_rejected(identifier: str) -> None:
    with pytest.raises(SignalSchemaError):
        SignalDescriptor(
            identifier=identifier,
            display_name="Example",
            path=("vehicle", "example"),
            data_type="numeric",
            source_id="source-01",
        )


@pytest.mark.parametrize("shape", [(), (3,), (4, 4), (2, 3, 4)])
def test_valid_shapes_are_accepted(shape: tuple[int, ...]) -> None:
    descriptor = SignalDescriptor(
        identifier="imu.vector",
        display_name="Vector",
        path=("vehicle", "imu"),
        data_type="vector",
        source_id="source-01",
        shape=shape,
    )

    assert descriptor.shape == shape


@pytest.mark.parametrize("shape", [(0,), (-1,), (True,), ("3",)])
def test_invalid_shapes_are_rejected(shape: tuple[object, ...]) -> None:
    with pytest.raises(SignalSchemaError):
        SignalDescriptor(
            identifier="imu.vector",
            display_name="Vector",
            path=("vehicle", "imu"),
            data_type="vector",
            source_id="source-01",
            shape=cast(tuple[int, ...], shape),
        )


def test_sparse_mixed_rate_series_does_not_create_duplicate_rows() -> None:
    fast = SignalSeries.from_samples(
        "imu.acceleration.x",
        [SignalSample(0, 1.0), SignalSample(10_000_000, 1.1), SignalSample(20_000_000, 1.2)],
    )
    slow = SignalSeries.from_samples(
        "power.battery.low",
        [SignalSample(0, False), SignalSample(20_000_000, True)],
    )

    assert [sample.timestamp_ns for sample in fast.samples] == [0, 10_000_000, 20_000_000]
    assert [sample.timestamp_ns for sample in slow.samples] == [0, 20_000_000]
    assert len(fast.samples) + len(slow.samples) == 5


def test_unavailable_sample_requires_explicit_reason_or_quality() -> None:
    sample = SignalSample(10, None, available=False, quality="not-reported")

    assert sample.value is None
    assert not sample.available
    assert sample.quality == "not-reported"


def test_invalid_unit_and_rate_are_rejected() -> None:
    with pytest.raises(SignalSchemaError, match="canonical_unit"):
        SignalDescriptor(
            identifier="engine.rpm",
            display_name="Engine RPM",
            path=("vehicle", "engine"),
            data_type="numeric",
            source_id="source-01",
            canonical_unit="rpm value",
        )
    with pytest.raises(SignalSchemaError, match="nominal_rate_hz"):
        SignalDescriptor(
            identifier="engine.rpm",
            display_name="Engine RPM",
            path=("vehicle", "engine"),
            data_type="numeric",
            source_id="source-01",
            nominal_rate_hz=0,
        )
