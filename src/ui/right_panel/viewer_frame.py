from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QTabWidget,
    QFrame,
    QSizePolicy,
    QVBoxLayout,
)

class ViewFrame(QFrame):
    def __init__(self) -> None:
        super().__init__()
        # --- Middle: Viewer Pane ---
        self.setObjectName("viewer_frame")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        vf_layout = QVBoxLayout()
        vf_layout.setContentsMargins(8, 8, 8, 8)
        self._viewer_label = QLabel("Line Graph")
        self._viewer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._viewer_label.setStyleSheet("font-size:20px; color: #1a73e8; font-weight:700;")
        vf_layout.addWidget(self._viewer_label)
        
        vf_layout.addStretch()
        self.setLayout(vf_layout)