"""Tests for CSV-to-model decoding outside the widget layer."""

from pathlib import Path

import pytest

from lbr_dashboard.core.log import LogSession
from lbr_dashboard.importers.csv_importer import CsvImporter


def test_csv_importer_decodes_rows_and_numeric_columns(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.csv"
    path.write_text(
        "\ufefftimestamp_ms,engine_rpm,note\n0,900,start\n10,,running\n", encoding="utf-8"
    )

    session = CsvImporter().import_session(path)

    assert session.headers == ("timestamp_ms", "engine_rpm", "note")
    assert session.rows == (("0", "900", "start"), ("10", "", "running"))
    assert session.numeric_column("timestamp_ms") == (0.0, 10.0)
    assert session.numeric_column("engine_rpm") == (900.0, None)
    assert session.numeric_column("note") == (None, None)


def test_csv_importer_returns_empty_model_for_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    session = CsvImporter().import_session(path)

    assert session.headers == ()
    assert session.rows == ()
    assert not session.numeric_columns


def test_log_session_freezes_numeric_columns() -> None:
    values = [1.0, 2.0]
    session = LogSession(("speed",), (("1",), ("2",)), {"speed": values})  # type: ignore[arg-type]
    values.append(3.0)

    assert session.numeric_column("speed") == (1.0, 2.0)
    with pytest.raises(TypeError):
        session.numeric_columns["other"] = ()  # type: ignore[index]
