"""
Entry point for the Local Meeting Notes application.
Initializes and runs the main application window.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from src.ui.main_window import MainWindow


def ensure_directories_exist():
    """Create input and output directories if they don't exist."""
    input_dir = Path("input")
    output_dir = Path("output")

    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)


def main():
    """Main application entry point."""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Local Meeting Notes Generator")
    app.setApplicationVersion("1.0.0")

    # Set application icon
    icon_path = Path("icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Ensure required directories exist
    ensure_directories_exist()

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run the application
    exit_code = app.exec_()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()