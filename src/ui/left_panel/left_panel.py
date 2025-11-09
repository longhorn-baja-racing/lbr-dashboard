import random
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem
from PyQt6.QtGui import QIcon, QAction


class LeftPanel(QWidget):

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # State
        state_label = QLabel("State")
        state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state_label.setStyleSheet("font-size: 15; color: #eee;")
        state_label.setAutoFillBackground(True)

        # Search
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search")
        search_action = QAction(QIcon("assets/icons/search_icon.png"), "Search", self)
        self.search_bar.setFixedHeight(35)
        self.search_bar.addAction(search_action, QLineEdit.ActionPosition.LeadingPosition)
        search_layout.addWidget(self.search_bar)

        # Tree widget for sensors
        self.data_tree = QTreeWidget()
        self.data_tree.setColumnCount(2)
        self.data_tree.setColumnWidth(0, 200)
        self.data_tree.setHeaderHidden(True)
        self.data_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) 
        self.data_tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  
        self.data_tree.header().setSectionResizeMode(0, self.data_tree.header().ResizeMode.Stretch)
        self.data_tree.header().setSectionResizeMode(1, self.data_tree.header().ResizeMode.ResizeToContents)
        self.data_tree.setStyleSheet("""
            QTreeWidget {
                font-size: 11pt;
            }
            QTreeWidget::item {
                height: 18px;
                padding: 2px;
            }
        """)

        self.search_bar.textChanged.connect(self.filter_tree)

        # Test Data
        sensor_data = {
            "Engine": {
                "RPM": 3540,
                "Temperature": 92.4,
                "Fuel": {
                    "Level": 47.2,
                    "Consumption": 8.1,
                    "Pressure": 3.6,
                    "Injector": {
                        "Pulse Width": 2.4,
                        "Duty Cycle": 85.3
                    }
                },
                "Oil": {
                    "Pressure": 4.2,
                    "Temperature": 87.1,
                    "Viscosity": 10.5
                }
            },

            "Transmission": {
                "Gear": 3,
                "Fluid": {
                    "Temperature": 78.6,
                    "Pressure": 2.9
                },
                "Clutch": {
                    "Engagement": 97.2,
                    "Slip": 0.03
                }
            },

            "Battery": {
                "Voltage": 12.6,
                "Current": 5.4,
                "Temperature": 35.2,
                "Cells": {
                    "Cell 1": 4.18,
                    "Cell 2": 4.19,
                    "Cell 3": 4.17
                }
            },

            "Brakes": {
                "Front": {
                    "Pressure": 5.6,
                    "Temperature": 120.5,
                    "Pad Wear": 42.1
                },
                "Rear": {
                    "Pressure": 4.8,
                    "Temperature": 98.2,
                    "Pad Wear": 37.6
                }
            },

            "Suspension": {
                "Front Left": {
                    "Travel": 32.5,
                    "Damping": 6.4
                },
                "Front Right": {
                    "Travel": 31.9,
                    "Damping": 6.6
                },
                "Rear Left": {
                    "Travel": 28.3,
                    "Damping": 6.1
                },
                "Rear Right": {
                    "Travel": 27.8,
                    "Damping": 6.2
                }
            },

            "Tires": {
                "Front Left": {
                    "Pressure": 32.5,
                    "Temperature": 68.4,
                    "Wear": 21.5
                },
                "Front Right": {
                    "Pressure": 32.3,
                    "Temperature": 67.9,
                    "Wear": 20.8
                },
                "Rear Left": {
                    "Pressure": 30.7,
                    "Temperature": 70.2,
                    "Wear": 23.4
                },
                "Rear Right": {
                    "Pressure": 30.6,
                    "Temperature": 71.0,
                    "Wear": 24.1
                }
            },

            "GPS": {
                "Latitude": 30.2672,
                "Longitude": -97.7431,
                "Altitude": 153.0,
                "Speed": 45.3,
                "Heading": 182.4
            },

            "Telemetry": {
                "Uptime": 15432,
                "Signal Strength": 83.5,
                "Packet Loss": 0.2,
                "Logging": {
                    "File Size": "24.3 MB",
                    "Frames Recorded": 12043
                }
            }
        }


        self.populate_tree(sensor_data)

        layout.addWidget(state_label)
        layout.addLayout(search_layout)
        layout.addWidget(self.data_tree)
        self.setLayout(layout)

        self.setStyleSheet("background-color: #000;")

    
    def populate_tree(self, data, parent=None):
        """Recursively populate tree from nested dictionary"""
        if parent is None:
            parent = self.data_tree

        for key, val in data.items():
            if isinstance(val, dict):
                item = QTreeWidgetItem(parent, [key, ""])
                self.populate_tree(val, item)
            else:
                leaf_item = QTreeWidgetItem(parent, [key, str(val)])
                leaf_item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)

    def filter_tree(self, text):
        text = text.lower()
        root = self.data_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self.filter_item(root.child(i), text)

    def filter_item(self, item, text):
        match = text in item.text(0).lower()
        for i in range(item.childCount()):
            child_match = self.filter_item(item.child(i), text)
            match = match or child_match
        item.setHidden(not match)
        return match

