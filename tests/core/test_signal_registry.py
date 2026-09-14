"""Deterministic hierarchy and search behavior for the signal registry."""

from lbr_dashboard.core import SignalDescriptor, SignalRegistry, SignalSchema


def _descriptor(identifier: str, name: str, path: tuple[str, ...]) -> SignalDescriptor:
    return SignalDescriptor(
        identifier=identifier,
        display_name=name,
        path=path,
        data_type="numeric",
        source_id="pico-telemetry",
        canonical_unit="m/s^2",
    )


def test_registry_orders_descriptors_and_derives_search_tokens() -> None:
    registry = SignalRegistry()
    registry.register(_descriptor("imu.acceleration.z", "Acceleration Z", ("vehicle", "imu")))
    registry.register(_descriptor("imu.acceleration.x", "Acceleration X", ("vehicle", "imu")))
    registry.register(_descriptor("power.voltage", "Battery Voltage", ("vehicle", "power")))

    assert [item.identifier for item in registry.descriptors()] == [
        "imu.acceleration.x",
        "imu.acceleration.z",
        "power.voltage",
    ]
    assert [item.identifier for item in registry.search("battery voltage")] == ["power.voltage"]
    assert [item.identifier for item in registry.search("")] == [
        "imu.acceleration.x",
        "imu.acceleration.z",
        "power.voltage",
    ]


def test_registry_groups_by_hierarchical_path_without_subsystem_enum() -> None:
    schema = SignalSchema(
        schema_version=1,
        signals=(
            _descriptor("future.suspension.travel", "Suspension Travel", ("vehicle", "suspension")),
            _descriptor("imu.acceleration.x", "Acceleration X", ("vehicle", "imu")),
        ),
    )
    registry = SignalRegistry(schema)

    assert [item.identifier for item in registry.under_path(("vehicle", "suspension"))] == [
        "future.suspension.travel"
    ]


def test_unknown_schema_fields_can_be_rejected_explicitly() -> None:
    payload = {
        "schema_version": 1,
        "future_schema_option": True,
        "signals": [
            {
                "id": "imu.acceleration.x",
                "display_name": "Acceleration X",
                "path": ["vehicle", "imu"],
                "type": "numeric",
                "source_id": "pico-telemetry",
                "future_signal_option": "keep-me",
            }
        ],
    }

    schema = SignalSchema.from_dict(payload)
    assert schema.extra["future_schema_option"] is True
    assert schema.signals[0].unknown_fields["future_signal_option"] == "keep-me"
