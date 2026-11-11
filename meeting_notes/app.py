"""Qt application bootstrap."""

from __future__ import annotations

import sys
from typing import List, Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from meeting_notes import __version__
from meeting_notes.config import APP_NAME, AppConfig, app_root, resource_root
from meeting_notes.ui.main_window import MainWindow
from meeting_notes.ui.preferences import APPLICATION, ORGANIZATION


def run(argv: Optional[List[str]] = None) -> int:
    """Start the GUI and block until it closes; return the Qt exit code."""
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName(APPLICATION)
    app.setOrganizationName(ORGANIZATION)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)

    icon_path = resource_root() / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    root = app_root()
    try:
        AppConfig.discover(root).ensure_directories()
    except OSError:
        pass

    window = MainWindow(root)
    window.show()
    return app.exec_()
