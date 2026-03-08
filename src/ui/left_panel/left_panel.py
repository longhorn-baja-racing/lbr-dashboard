from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QListWidget


class LeftPanel(QWidget):
    """Left panel widget for the dashboard, shows CSV column names."""

    def __init__(self) -> None:
        super().__init__()

        # List widget for column names
        self.list_widget = QListWidget()

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
