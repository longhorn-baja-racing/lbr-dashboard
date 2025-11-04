from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class LeftPanel(QWidget):
    """Temporary left panel for the dashboard."""

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Left Panel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #000;")

        layout.addWidget(label)
        self.setLayout(layout)

        self.setStyleSheet("background-color: #ddd;")
