from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class RightPanel(QWidget):
    """Temporary right panel widget for the dashboard."""

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Right Panel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #000;")

        layout.addWidget(label)
        self.setLayout(layout)

        self.setStyleSheet("background-color: #eee;")
