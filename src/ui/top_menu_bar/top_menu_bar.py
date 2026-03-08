from typing import Optional

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QMenuBar, QApplication, QFileDialog


class TopMenuBar(QMenuBar):
    """Top menu bar for the dashboard."""

    def __init__(self, main_window) -> None:
        super().__init__()

        self.main_window = main_window
        self._create_file_menu()

    def _create_file_menu(self):
        file_menu = self.addMenu("&File")

        # Open CSV action
        open_action = QAction("&Open", self)
        open_action.triggered.connect(self.main_window.open_csv)  # <-- send to MainWindow
        file_menu.addAction(open_action)


        save_action: QAction = QAction("&Save", self)

        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.main_window.close)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)




    '''
    def _create_file_menu(self) -> None:
        """Initialize the menu bar components."""

        file_menu: Optional[QMenu] = self.addMenu("&File")

        # Placeholders
        new_action: QAction = QAction("&New", self)
        open_action: QAction = QAction("&Open", self)
        save_action: QAction = QAction("&Save", self)
        exit_action: QAction = QAction("E&xit", self)

        exit_action.triggered.connect(QApplication.quit)

        if file_menu is not None:
            file_menu.addAction(new_action)
            file_menu.addAction(open_action)
            file_menu.addAction(save_action)

            file_menu.addSeparator()

            file_menu.addAction(exit_action)'''
            
