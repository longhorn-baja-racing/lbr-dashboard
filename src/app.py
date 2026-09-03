import signal
import sys

from PyQt6.QtWidgets import QApplication

from ui import MainWindow


def main() -> None:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
