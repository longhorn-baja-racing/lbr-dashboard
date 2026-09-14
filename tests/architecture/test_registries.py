"""Behavioral tests for the internal extension registries."""

import pytest

from lbr_dashboard.core import FactoryError, Registry, RegistryBundle


def test_registry_rejects_duplicates_and_returns_sorted_ids() -> None:
    registry = Registry[object]("widgets")
    registry.register("zeta", object)
    registry.register("alpha", object)

    assert registry.identifiers() == ("alpha", "zeta")
    with pytest.raises(ValueError, match="already registered"):
        registry.register("alpha", object)


def test_registry_unknown_id_is_descriptive() -> None:
    registry = Registry[object]("importers")

    with pytest.raises(KeyError, match="Unknown identifier 'csv'"):
        registry.create("csv")


def test_registry_wraps_factory_failures() -> None:
    def broken_factory() -> object:
        raise RuntimeError("not configured")

    registry = Registry[object]("sources")
    registry.register("broken", broken_factory)

    with pytest.raises(FactoryError, match="Factory 'broken'.*registry 'sources'.*not configured"):
        registry.create("broken")


def test_each_application_gets_independent_registry_bundle() -> None:
    class DemoWidget:
        widget_id = "demo"

        def create(self, parent=None) -> object:
            del parent
            return object()

    first = RegistryBundle()
    second = RegistryBundle()
    first.widgets.register("demo", DemoWidget)

    assert first.widgets.identifiers() == ("demo",)
    assert second.widgets.identifiers() == ()


def test_source_and_widget_can_register_without_shell_changes() -> None:
    class DemoSource:
        source_id = "demo"

        def start(self, events, cancellation) -> None:
            del events, cancellation

        def stop(self) -> None:
            pass

    class DemoWidget:
        widget_id = "demo"

        def create(self, parent=None) -> object:
            del parent
            return object()

    registries = RegistryBundle()
    registries.telemetry_sources.register("demo", DemoSource)
    registries.widgets.register("demo", DemoWidget)

    assert isinstance(registries.telemetry_sources.create("demo"), DemoSource)
    assert isinstance(registries.widgets.create("demo"), DemoWidget)
