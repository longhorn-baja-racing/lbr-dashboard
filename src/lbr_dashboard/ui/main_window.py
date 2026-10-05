"""Temporary dashboard shell for the P0 foundation milestone."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMainWindow, QSplitter

from ..core.log import LogImporter
from .constants import MIN_PANEL_WIDTH
from .left_panel import LeftPanel
from .right_panel import RightPanel
from .top_menu_bar import TopMenuBar


class MainWindow(QMainWindow):
    """Main application window that coordinates imported data and presentation."""

    def __init__(self, importer: LogImporter) -> None:
        super().__init__()
        self._importer = importer
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
        """Ask the importer to decode a CSV, then pass its model to the panels."""

        log = self._importer.import_session(file_path)
        if not log.headers:
            return

        self.left_panel.set_columns(list(log.headers))
        self.right_panel.set_log(log)
        self.left_panel.list_widget.setCurrentRow(0)
        self._select_column(0)
