from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QSplitter, QFileDialog

from models.constants import window_constants

from .left_panel import LeftPanel
from .right_panel import RightPanel
from .top_menu_bar import TopMenuBar
import csv


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("LBR Dashboard")
        self.resize(1200, 700)

        # Top menu bar
        top_menu_bar = TopMenuBar(self)
        self.setMenuBar(top_menu_bar)

        # Left and Right Panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.left_panel = LeftPanel()
        self.right_panel = RightPanel()

        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)

        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        # 25/75 split
        splitter.setSizes([300, 900])

        splitter.setOpaqueResize(True)
        splitter.setHandleWidth(4)

        self.left_panel.setMinimumWidth(window_constants.MIN_PANEL_WIDTH)
        self.right_panel.setMinimumWidth(window_constants.MIN_PANEL_WIDTH)

        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #c0c0c0;
            }
            QSplitter::handle:hover {
                background-color: #a0a0a0;
            }
        """)

        self.setCentralWidget(splitter)
        self.left_panel.list_widget.currentRowChanged.connect(
            self.right_panel.highlight_column
        )

    def open_csv(self):
        """Open a CSV file and send data to panels."""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open CSV File",
            "",
            "CSV Files (*.csv)"
        )

        if not file_path:
            return

        # Read CSV
        with open(file_path, newline="") as f:
            reader = csv.reader(f)
            data = list(reader)

        if not data:
            return

        headers = data[0]
        rows = data[1:]

        # Send to panels
        self.left_panel.set_columns(headers)
        self.right_panel.set_data(headers, rows)
