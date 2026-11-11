"""Qt style sheets for the main window."""

WINDOW = """
    QMainWindow {
        background-color: #dcf2ee;
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
    }
    QGroupBox {
        font-weight: bold;
        border: 2px solid #8fbcc9;
        border-radius: 8px;
        margin-top: 1ex;
        padding-top: 10px;
        background-color: #d7f7f0;
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
        color: #006666;
        font-family: 'Times New Roman', serif;
        font-weight: bold;
        font-size: 13pt;
    }
    QPushButton {
        background-color: #a3e9da;
        border: 2px solid #7fc2b7;
        border-radius: 12px;
        padding: 10px;
        font-weight: bold;
        min-height: 35px;
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
    }
    QPushButton#generateButton {
        background-color: #8dd8c8;
        border: 2px solid #6bb5a3;
        border-radius: 15px;
        padding: 10px;
        font-weight: bold;
        font-size: 16pt;
        min-height: 40px;
        font-family: 'Times New Roman', serif;
    }
    QPushButton#generateButton:hover {
        background-color: #b3f2e5;
    }
    QPushButton#generateButton:pressed {
        background-color: #b3f2e5;
    }
    QPushButton:hover {
        background-color: #9de3d3;
    }
    QPushButton:pressed {
        background-color: #7bc9ba;
    }
    QPushButton:disabled {
        background-color: #c0e0da;
        color: #888888;
    }
    QComboBox {
        border: 2px solid #7fc2b7;
        border-radius: 8px;
        padding: 8px;
        background-color: white;
        min-height: 35px;
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
    }
    QComboBox:hover {
        background-color: #f0f9f7;
    }
    QComboBox:focus {
        border: 2px solid #5fa897;
        background-color: #9de3d3;
    }
    QProgressBar {
        border: 2px solid #7fc2b7;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        color: #006666;
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
    }
    QProgressBar::chunk {
        background-color: #79c7b5;
        border-radius: 6px;
    }
    QTextEdit {
        border: 2px solid #7fc2b7;
        border-radius: 8px;
        background-color: white;
        font-family: 'Times New Roman', serif;
        font-size: 11pt;
    }
    QLabel {
        color: #004d4d;
        font-weight: bold;
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
    }
"""

CENTRAL_WIDGET = (
    "background-color: #dcf2ee; font-family: 'Times New Roman', serif; font-size: 12pt;"
)

TITLE = """
    font-family: 'Times New Roman', serif;
    font-size: 32px;
    font-weight: bold;
    color: #004d4d;
    padding: 15px;
    background-color: #9de3d3;
    border-radius: 10px;
    margin-bottom: 10px;
"""

FILE_LABEL = "font-family: 'Times New Roman', serif; font-weight: bold; font-size: 12pt;"

TRANSCRIBE_BUTTON = """
    QPushButton {
        background-color: #9de3d3;
        border: 2px solid #7fc2b7;
        border-radius: 12px;
        padding: 10px;
        font-weight: bold;
        min-height: 35px;
        font-family: 'Times New Roman', serif;
        font-size: 12pt;
    }
    QPushButton:hover {
        background-color: #b3f2e5;
    }
    QPushButton:pressed {
        background-color: #7bc9ba;
    }
    QPushButton:disabled {
        background-color: #c0e0da;
        color: #888888;
    }
"""

GENERATE_BUTTON = """
    QPushButton#generateButton {
        background-color: #9de3d3;
        border: 2px solid #6bb5a3;
        border-radius: 15px;
        padding: 10px;
        font-weight: bold;
        font-size: 16pt;
        min-height: 40px;
        font-family: 'Times New Roman', serif;
    }
    QPushButton#generateButton:hover {
        background-color: #b3f2e5;
    }
    QPushButton#generateButton:pressed {
        background-color: #7bc9ba;
    }
"""
