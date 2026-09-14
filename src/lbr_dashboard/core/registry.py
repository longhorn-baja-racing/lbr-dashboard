"""Deterministic, per-application registries for internal extensions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Generic, TypeVar

T = TypeVar("T")
Factory = Callable[..., T]


class RegistryError(ValueError):
    """Base error for invalid registry operations."""


class FactoryError(RuntimeError):
    """Raised when a registered factory cannot create its value."""

    def __init__(self, registry_name: str, identifier: str, cause: Exception) -> None:
        self.registry_name = registry_name
        self.identifier = identifier
        self.cause = cause
        super().__init__(
            f"Factory '{identifier}' in registry '{registry_name}' failed: "
            f"{type(cause).__name__}: {cause}"
        )


class Registry(Generic[T]):
    """Map stable identifiers to factories with explicit failure behavior.

    Registries are ordinary objects owned by an application context.  They do
    not use module-level state or service-locator behavior.
    """

    def __init__(self, name: str) -> None:
        if not name.strip():
            raise RegistryError("Registry name must not be empty")
        self.name = name
        self._factories: dict[str, Factory[T]] = {}

    def register(self, identifier: str, factory: Factory[T]) -> None:
        """Register a factory, rejecting blank or duplicate identifiers."""

        normalized = identifier.strip()
        if not normalized:
            raise RegistryError(f"Registry '{self.name}' requires a non-empty identifier")
        if normalized in self._factories:
            raise RegistryError(
                f"Identifier '{normalized}' is already registered in registry '{self.name}'"
            )
        self._factories[normalized] = factory

    def unregister(self, identifier: str) -> None:
        """Remove an identifier when an application explicitly unloads it."""

        try:
            del self._factories[identifier]
        except KeyError as exc:
            raise KeyError(f"Unknown identifier '{identifier}' in registry '{self.name}'") from exc

    def get(self, identifier: str) -> Factory[T]:
        """Return a factory or raise a stable, descriptive unknown-ID error."""

        try:
            return self._factories[identifier]
        except KeyError as exc:
            raise KeyError(f"Unknown identifier '{identifier}' in registry '{self.name}'") from exc

    def create(self, identifier: str, *args: object, **kwargs: object) -> T:
        """Create a registered value and wrap provider failures with context."""

        factory = self.get(identifier)
        try:
            return factory(*args, **kwargs)
        except Exception as exc:
            raise FactoryError(self.name, identifier, exc) from exc

    def identifiers(self) -> tuple[str, ...]:
        """Return identifiers in deterministic order."""

        return tuple(sorted(self._factories))

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._factories

    def __iter__(self) -> Iterator[str]:
        return iter(self.identifiers())

    def __len__(self) -> int:
        return len(self._factories)
