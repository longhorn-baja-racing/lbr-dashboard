"""Temporary dashboard shell for the P0 foundation milestone."""

from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMainWindow, QSplitter

from .constants import MIN_PANEL_WIDTH
from .left_panel import LeftPanel
from .right_panel import RightPanel
from .top_menu_bar import TopMenuBar


class MainWindow(QMainWindow):
    """Main application window.

    CSV loading remains a deliberately small compatibility path for this shell.
    It will move behind importer/source interfaces in P0 issues #17 and #20.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LBR Dashboard")
        self.resize(1200, 700)

        self.setMenuBar(TopMenuBar(self))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_panel = LeftPanel()
        self.right_panel = RightPanel()
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([300, 900])
        splitter.setOpaqueResize(True)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(
            """
            QSplitter::handle { background-color: #c0c0c0; }
            QSplitter::handle:hover { background-color: #a0a0a0; }
            """
        )

        self.left_panel.setMinimumWidth(MIN_PANEL_WIDTH)
        self.right_panel.setMinimumWidth(MIN_PANEL_WIDTH)
        self.setCentralWidget(splitter)

        self.left_panel.list_widget.currentRowChanged.connect(self._select_column)

    def _select_column(self, column_index: int) -> None:
        """Highlight and plot the selected column, including the first selection."""

        self.right_panel.highlight_column(column_index)
        if column_index < 0:
            return

        item = self.left_panel.list_widget.item(column_index)
        if item is not None:
            self.right_panel.plot_column(item.text())

    def open_csv(self) -> None:
        """Open a CSV file and display its columns and rows."""

        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.load_csv(Path(file_path))

    def load_csv(self, file_path: Path) -> None:
        """Load a CSV directly, primarily for the foundation smoke test."""

        with file_path.open(newline="", encoding="utf-8-sig") as csv_file:
            rows = list(csv.reader(csv_file))

        if not rows:
            return

        headers, data = rows[0], rows[1:]
        self.left_panel.set_columns(headers)
        self.right_panel.set_data(headers, data)
        if headers:
            self.left_panel.list_widget.setCurrentRow(0)
            self._select_column(0)
