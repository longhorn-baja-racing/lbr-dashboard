"""Application menu bar."""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenuBar


class TopMenuBar(QMenuBar):
    """File menu for the dashboard shell."""

    def __init__(self, main_window) -> None:
        super().__init__(main_window)
        file_menu = self.addMenu("&File")

        open_action = QAction("&Open", self)
        open_action.triggered.connect(main_window.open_csv)
        file_menu.addAction(open_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(main_window.close)
        file_menu.addAction(exit_action)
