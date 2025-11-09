from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QTabWidget,
    QWidget,
    QSizePolicy
)

class TabBar(QTabWidget):
    def __init__(self) -> None:
        # --- Top: Tab bar ---
        super().__init__()
        self.setObjectName("right_top_tabs")
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabWidget::tab-bar { alignment: left; }
            QTabBar::tab {
                padding: 8px 20px;
                margin: 2px 2px 0 2px;
                border: 2px solid #c0c0c0;
                border-radius: 6px;
                background: #f0f0f0;
                font-size: 14px;
                font-weight: bold;
            }
            QTabBar::tab:hover { 
                background: #e0e0e0;
                border-color: #1a73e8;
            }
            QTabBar::tab:selected {
                background: #1a73e8;
                border-color: #1a73e8;
                color: white;
            }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Add tab buttons without content pages
        for name in ("Line Graph", "Odometry", "3D Field"):
            self.addTab(QWidget(), name)
            
        # Remove the empty content area under the tabs
        self.setDocumentMode(True)
        