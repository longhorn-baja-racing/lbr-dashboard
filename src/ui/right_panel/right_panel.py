from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

from .tab_bar import TabBar
from .viewer_frame import ViewFrame
from .bottom_panel import BottomPanel

class RightPanel(QWidget):
    """Right panel widget with three vertical partitions:

    - Top: tab bar for choosing the data view
    - Middle: main viewer pane (graphs)
    - Bottom: control pane showing car-axis data split into three columns
    """

    def __init__(self) -> None:
        super().__init__()
        self._viewer_label = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)
        
        tabs = TabBar()
        viewer_frame = ViewFrame()
        control_frame = BottomPanel()
        self._viewer_label = viewer_frame.findChild(QLabel)
        
        # Connect tab change to update viewer label
        tabs.currentChanged.connect(lambda index: self._viewer_label.setText(tabs.tabText(index)))
        
        # Create splitter for resizable viewer and control panels
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(viewer_frame)
        splitter.addWidget(control_frame)
        
        # Set initial sizes (viewer gets more space)
        splitter.setSizes([700, 300])
        
        # Make the splitter handle visible and easier to grab
        splitter.setStyleSheet("""
            QSplitter::handle {
                height: 4px;
                background-color: #e0e0e0;
            }
            QSplitter::handle:hover {
                background-color: #1a73e8;
            }
        """)

        # Add widgets to root layout: top (tabs) and splitter (viewer + controls)
        root.addWidget(tabs)
        root.addWidget(splitter)
        self.setLayout(root)

        # Additional styling for frames and controls
        self.setStyleSheet("""
            #viewer_frame {
                background: #f8fbff;
                border: 2px solid #1a73e8;
                border-radius: 4px;
            }
            #control_frame {
                background: #f7fff7;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
            }
            QGroupBox {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                margin-top: 0.5em;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)