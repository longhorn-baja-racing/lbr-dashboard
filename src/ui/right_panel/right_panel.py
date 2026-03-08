from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem


class RightPanel(QWidget):
    """Right panel widget for the dashboard, shows CSV data."""

    def __init__(self) -> None:
        super().__init__()

        # Table to display CSV
        self.table = QTableWidget()

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
        self.setLayout(layout)

        # Background style
        self.setStyleSheet("background-color: #3a3a3a; color: #ffffff;")

    def set_data(self, headers, rows):
        """Populate the table with CSV headers and rows."""

        self.table.setColumnCount(len(headers))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(headers)

        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(value))
