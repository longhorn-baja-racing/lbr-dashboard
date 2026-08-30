"""Helpers for loading package resources without relying on the checkout path."""

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path


def resource_text(name: str, *, encoding: str = "utf-8") -> str:
    """Return a UTF-8 text resource bundled with the application."""

    return files("lbr_dashboard").joinpath(name).read_text(encoding=encoding)


def resource_bytes(name: str) -> bytes:
    """Return a binary resource bundled with the application."""

    return files("lbr_dashboard").joinpath(name).read_bytes()


@contextmanager
def resource_path(name: str) -> Iterator[Path]:
    """Temporarily expose a bundled resource as a filesystem path."""

    with as_file(files("lbr_dashboard").joinpath(name)) as path:
        yield path
