from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QSizePolicy,
    QHBoxLayout,
    QVBoxLayout,
    QGroupBox,
    QLabel,
)

class BottomPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("control_frame")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(120)
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(6, 6, 6, 6)
        control_layout.setSpacing(8)

        for title in ("Left Axis", "Discrete Fields", "Right Axis"):
            group = QGroupBox(title)
            group.setStyleSheet("QGroupBox{font-weight:700}")
            g_layout = QVBoxLayout()
            g_layout.setContentsMargins(8, 8, 8, 8)
            placeholder = QLabel("(data)")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color:#666; font-size:14px;")
            g_layout.addWidget(placeholder)
            g_layout.addStretch()
            group.setLayout(g_layout)
            control_layout.addWidget(group)

        self.setLayout(control_layout)