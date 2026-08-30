"""Application lifecycle and the supported desktop entry point."""

from __future__ import annotations

import signal
import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    """Create or return the process QApplication instance."""

    application = QApplication.instance()
    if isinstance(application, QApplication):
        return application
    return QApplication(list(sys.argv if argv is None else argv))


def create_main_window() -> MainWindow:
    """Create the application shell without showing it."""

    return MainWindow()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the dashboard and return the Qt event-loop exit code."""

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    application = create_application(argv)
    window = create_main_window()
    window.show()
    return application.exec()
