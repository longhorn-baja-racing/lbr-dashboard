from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QSplitter

from models.constants import window_constants

from .left_panel import LeftPanel
from .right_panel import RightPanel
from .top_menu_bar import TopMenuBar


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("LBR Dashboard")
        self.resize(1200, 700)

        # Top menu bar
        top_menu_bar = TopMenuBar()
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
