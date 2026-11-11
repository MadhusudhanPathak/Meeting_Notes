"""Dialog for downloading Whisper and Ollama models from inside the application."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Optional

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meeting_notes.core.control import JobControl
from meeting_notes.core.downloads import WhisperModelSpec, available_whisper_models
from meeting_notes.ui import styles
from meeting_notes.ui.workers import DownloadWorker

OLLAMA_LIBRARY_URL = "https://ollama.com/library"
SUGGESTED_OLLAMA_MODELS = (
    "llama3.2:3b",
    "llama3.1:8b",
    "qwen2.5:7b",
    "gemma3:4b",
    "mistral:7b",
    "phi4-mini",
)
_DEFAULT_WHISPER_MODEL = "medium"


class DownloadDialog(QDialog):
    """Lets the user fetch Whisper models (Hugging Face) and Ollama models."""

    def __init__(
        self,
        models_dir: Path,
        installed_whisper: Iterable[str],
        installed_ollama: Iterable[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Download Models")
        self.setMinimumWidth(720)
        self.setStyleSheet(styles.DIALOG)
        self._models_dir = models_dir
        self._installed_whisper = set(installed_whisper)
        self._installed_ollama = set(installed_ollama)
        self._worker: Optional[DownloadWorker] = None
        self._control: Optional[JobControl] = None
        self.downloaded_any = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        whisper_group = QGroupBox("Transcription models (Whisper, from Hugging Face)")
        whisper_layout = QHBoxLayout()
        self.whisper_combo = QComboBox()
        for spec in available_whisper_models(sys.platform == "win32"):
            installed = " - installed" if spec.filename in self._installed_whisper else ""
            self.whisper_combo.addItem(spec.label + installed, spec)
            if spec.name == _DEFAULT_WHISPER_MODEL:
                self.whisper_combo.setCurrentIndex(self.whisper_combo.count() - 1)
        self.whisper_button = QPushButton("Download")
        self.whisper_button.clicked.connect(self._download_whisper)
        whisper_layout.addWidget(self.whisper_combo, 1)
        whisper_layout.addWidget(self.whisper_button)
        whisper_group.setLayout(whisper_layout)
        layout.addWidget(whisper_group)

        ollama_group = QGroupBox("Note-generation models (Ollama)")
        ollama_layout = QVBoxLayout()
        row = QHBoxLayout()
        self.ollama_combo = QComboBox()
        self.ollama_combo.setEditable(True)
        self.ollama_combo.addItems(SUGGESTED_OLLAMA_MODELS)
        self.ollama_button = QPushButton("Download")
        self.ollama_button.clicked.connect(self._download_ollama)
        row.addWidget(self.ollama_combo, 1)
        row.addWidget(self.ollama_button)
        ollama_layout.addLayout(row)
        hint = QLabel(
            "Type any model name. Browse all models at "
            f"<a href='{OLLAMA_LIBRARY_URL}'>{OLLAMA_LIBRARY_URL}</a>. Ollama must be running."
        )
        hint.setOpenExternalLinks(True)
        hint.setWordWrap(True)
        hint.setStyleSheet("font-weight: normal;")
        ollama_layout.addWidget(hint)
        ollama_group.setLayout(ollama_layout)
        layout.addWidget(ollama_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Choose a model to download.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-weight: normal;")
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.cancel_button = QPushButton("Cancel Download")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    def _download_whisper(self) -> None:
        spec: WhisperModelSpec = self.whisper_combo.currentData()
        if spec.filename in self._installed_whisper:
            reply = QMessageBox.question(
                self, "Already Installed",
                f"{spec.filename} is already in the input folder. Download it again?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        control = JobControl()
        self._start(
            DownloadWorker(control, whisper_spec=spec, destination=self._models_dir, parent=self),
            control,
        )

    def _download_ollama(self) -> None:
        name = self.ollama_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "No Model", "Please enter an Ollama model name.")
            return
        if name in self._installed_ollama:
            self.status_label.setText(f"'{name}' is already installed; checking for updates...")
        control = JobControl()
        self._start(DownloadWorker(control, ollama_model=name, parent=self), control)

    def _start(self, worker: DownloadWorker, control: JobControl) -> None:
        self._control = control
        self._worker = worker
        worker.progress.connect(self._on_progress)
        worker.status.connect(self.status_label.setText)
        worker.succeeded.connect(self._on_succeeded)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(worker.deleteLater)
        self._set_busy(True)
        self.progress_bar.setRange(0, 0)
        worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        if total:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int(done * 100 / total))
            self.progress_bar.setFormat(f"%p%  ({_size(done)} of {_size(total)})")
        else:
            self.progress_bar.setRange(0, 0)

    def _on_succeeded(self, message: str) -> None:
        self.downloaded_any = True
        self._finish(message, 100)

    def _on_failed(self, message: str) -> None:
        self._finish(message, 0)

    def _finish(self, message: str, value: int) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        self._worker = None
        self._control = None
        self._set_busy(False)

    def _cancel(self) -> None:
        if self._control is not None:
            self.status_label.setText("Cancelling...")
            self._control.cancel()

    def _set_busy(self, busy: bool) -> None:
        for widget in (
            self.whisper_combo, self.whisper_button, self.ollama_combo, self.ollama_button
        ):
            widget.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)

    def done(self, result: int) -> None:
        """Cancel any running download before the dialog closes."""
        if self._worker is not None and self._worker.isRunning():
            self._cancel()
            self._worker.wait()
        super().done(result)


def _size(byte_count: int) -> str:
    value = float(byte_count)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit in ("B", "KB") else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"

