from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QListWidget


class LeftPanel(QWidget):
    """Left panel widget for the dashboard, shows CSV column names."""

    column_selected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

        # List widget for column names
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget::item:selected {
                background-color: #0078d4;
            }
            QListWidget::item:hover {
                background-color: #444444;
            }
        """)
        self.list_widget.currentTextChanged.connect(self.column_selected.emit)

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        # Background style
        self.setStyleSheet("background-color: #2e2e2e; color: #ffffff;")

    def set_columns(self, columns):
        """Populate the left panel with column names."""
        self.list_widget.clear()
        self.list_widget.addItems(columns)
