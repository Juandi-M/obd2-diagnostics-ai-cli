from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from app.bootstrap.runtime import init_environment
from app.presentation.qt.app_vm import get_vm
from app.presentation.qt.shell.main_window import MainWindow
from app.presentation.qt.style import app_stylesheet


def main() -> int:
    init_environment()
    get_vm()  # Ensure container + viewmodels are initialized.
    app = QApplication(sys.argv)
    app.setStyleSheet(app_stylesheet())
    app.setFont(QFontDatabase.systemFont(QFontDatabase.GeneralFont))
    window = MainWindow()
    window.resize(980, 640)
    window.show()
    QTimer.singleShot(0, window.start_timers)
    return app.exec()


def run() -> int:
    return main()

