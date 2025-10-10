import sys
import signal

from PyQt6.QtWidgets import QApplication, QWidget


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("LHB Dashboard")
    window.resize(800, 600)

    window.show()

    sys.exit(app.exec())
