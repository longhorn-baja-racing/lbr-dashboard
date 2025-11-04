from typing import Optional

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QMenuBar


class TopMenuBar(QMenuBar):
    """Top menu bar for the dashboard."""

    def __init__(self) -> None:
        super().__init__()

        self._create_file_menu()

    def _create_file_menu(self) -> None:
        """Initialize the menu bar components."""

        file_menu: Optional[QMenu] = self.addMenu("&File")

        # Placeholders
        new_action: QAction = QAction("&New", self)
        open_action: QAction = QAction("&Open", self)
        save_action: QAction = QAction("&Save", self)
        exit_action: QAction = QAction("E&xit", self)

        if file_menu is not None:
            file_menu.addAction(new_action)
            file_menu.addAction(open_action)
            file_menu.addAction(save_action)

            file_menu.addSeparator()

            file_menu.addAction(exit_action)
