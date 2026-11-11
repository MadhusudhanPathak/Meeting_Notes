"""Qt application bootstrap."""

from __future__ import annotations

import sys
from typing import List, Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from meeting_notes import __version__
from meeting_notes.config import APP_NAME, AppConfig, app_root
from meeting_notes.ui.main_window import MainWindow


def run(argv: Optional[List[str]] = None) -> int:
    """Start the GUI and block until it closes; return the Qt exit code."""
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    root = app_root()
    icon_path = root / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    config = AppConfig.discover(root)
    config.ensure_directories()

    window = MainWindow(config)
    window.show()
    return app.exec_()
