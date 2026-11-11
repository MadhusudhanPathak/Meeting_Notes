"""Main application window: file selection, job orchestration, and result saving."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PyQt5.QtCore import QThread, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from meeting_notes.config import APP_NAME, AppConfig
from meeting_notes.core.note_generator import OLLAMA_DOWNLOAD_URL, NoteGenerationError, NoteGenerator
from meeting_notes.core.transcriber import AUDIO_EXTENSIONS, is_supported_audio_file
from meeting_notes.export.writer import OutputPaths, write_pdf, write_text
from meeting_notes.ui import styles
from meeting_notes.ui.workers import JobResult, NotesWorker, TranscriptionWorker

AUDIO_FILE_FILTER = "Audio Files ({})".format(" ".join(f"*{ext}" for ext in AUDIO_EXTENSIONS))
SUPPORTED_FORMATS = ", ".join(ext.lstrip(".").upper() for ext in AUDIO_EXTENSIONS)


class JobKind(Enum):
    TRANSCRIBE = "transcribe"
    NOTES = "notes"


@dataclass(frozen=True)
class _JobText:
    """User-facing messages for one job kind; ``{placeholders}`` are filled at runtime."""

    confirm_title: str
    confirm_single: str
    confirm_batch_title: str
    confirm_batch: str
    batch_item: str
    batch_item_failed: str
    batch_done: str
    failed_title: str
    failed_message: str
    succeeded: str


_JOB_TEXT = {
    JobKind.TRANSCRIBE: _JobText(
        confirm_title="Confirm Transcription",
        confirm_single="This will transcribe '{name}' using the selected model.\n\nContinue?",
        confirm_batch_title="Confirm Batch Transcription",
        confirm_batch=(
            "This will transcribe {count} audio files sequentially using the selected model."
            "\n\nContinue?"
        ),
        batch_item="Transcribing file {index}/{total}: {name}",
        batch_item_failed="Failed to transcribe file {index}: {name}",
        batch_done="Batch transcription completed!",
        failed_title="Transcription Failed",
        failed_message="The transcription process failed. Check the log for details.",
        succeeded="Successfully transcribed: {name}",
    ),
    JobKind.NOTES: _JobText(
        confirm_title="Confirm Processing",
        confirm_single=(
            "This will process '{name}' and generate notes using the selected model and prompt."
            "\n\nContinue?"
        ),
        confirm_batch_title="Confirm Batch Processing",
        confirm_batch=(
            "This will process {count} audio files sequentially using the selected model and "
            "prompt.\n\nContinue?"
        ),
        batch_item="Processing file {index}/{total}: {name}",
        batch_item_failed="Failed to process file {index}: {name}",
        batch_done="Batch processing completed!",
        failed_title="Processing Failed",
        failed_message="The note generation process failed. Check the log for details.",
        succeeded="Successfully processed: {name}",
    ),
}


@dataclass(frozen=True)
class _JobSettings:
    """Selections captured when a job starts, so a batch uses consistent inputs."""

    kind: JobKind
    files: Tuple[str, ...]
    is_batch: bool
    model_path: Path
    prompt_path: Optional[Path]
    ollama_model: str


class MainWindow(QMainWindow):
    """Top-level window that drives single-file and batch processing."""

    def __init__(self, config: AppConfig, note_generator: Optional[NoteGenerator] = None) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 900, 700)

        self._config = config
        self._note_generator = note_generator or NoteGenerator()
        self._selected_files: List[str] = []
        self._is_batch_selection = False
        self._job: Optional[_JobSettings] = None
        self._job_index = 0
        self._worker: Optional[QThread] = None
        self._transcription_available = False
        self._notes_available = False

        self._build_ui()
        self._check_dependencies()

    def _build_ui(self) -> None:
        self.setStyleSheet(styles.WINDOW)

        central_widget = QWidget()
        central_widget.setStyleSheet(styles.CENTRAL_WIDGET)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        title_label = QLabel(
            f"<span>{APP_NAME}</span><br>"
            "<span style='font-size: 16px;'>-by Madhusudhan Pathak</span>"
        )
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setTextFormat(Qt.RichText)
        title_label.setStyleSheet(styles.TITLE)
        main_layout.addWidget(title_label)

        main_layout.addWidget(self._build_controls())

        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setMinimumHeight(250)
        log_layout.addWidget(self.log_text_edit)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

    def _build_controls(self) -> QGroupBox:
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()

        audio_layout = QHBoxLayout()
        self.audio_file_label = QLabel("No file selected")
        self.audio_file_label.setWordWrap(True)
        self.audio_file_label.setStyleSheet(styles.FILE_LABEL)
        self.select_audio_button = QPushButton("Select Audio File")
        self.select_audio_button.clicked.connect(self._select_audio_file)
        self.select_batch_button = QPushButton("Select Multiple Files")
        self.select_batch_button.clicked.connect(self._select_batch_files)
        audio_layout.addWidget(self.audio_file_label)
        audio_layout.addWidget(self.select_audio_button)
        audio_layout.addWidget(self.select_batch_button)
        controls_layout.addLayout(audio_layout)

        self.ollama_model_combo = QComboBox()
        self.system_prompt_combo = QComboBox()
        self.model_bin_combo = QComboBox()
        for label, combo in (
            ("Ollama Model:", self.ollama_model_combo),
            ("System Prompt:", self.system_prompt_combo),
            ("Transcription Model:", self.model_bin_combo),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(combo)
            controls_layout.addLayout(row)

        buttons_layout = QHBoxLayout()
        self.transcribe_button = QPushButton("Transcribe Audio")
        self.transcribe_button.setObjectName("generateButton")
        self.transcribe_button.setEnabled(False)
        self.transcribe_button.setStyleSheet(styles.TRANSCRIBE_BUTTON)
        self.transcribe_button.clicked.connect(lambda: self._start_job(JobKind.TRANSCRIBE))
        buttons_layout.addWidget(self.transcribe_button, 1)

        self.make_notes_button = QPushButton("Generate Meeting Notes")
        self.make_notes_button.setObjectName("generateButton")
        self.make_notes_button.setEnabled(False)
        self.make_notes_button.setStyleSheet(styles.GENERATE_BUTTON)
        self.make_notes_button.clicked.connect(lambda: self._start_job(JobKind.NOTES))
        buttons_layout.addWidget(self.make_notes_button, 4)

        controls_layout.addLayout(buttons_layout)
        controls_group.setLayout(controls_layout)
        return controls_group

    def _log(self, message: str) -> None:
        self.log_text_edit.append(message)

    def _check_dependencies(self) -> None:
        """Validate dependencies, populate selectors, and enable the available features."""
        self._log("Status: Checking dependencies...")

        config_errors = self._config.validate()
        transcription_errors = self._config.transcription_errors()
        ollama_models, ollama_warning = self._fetch_ollama_models()

        self._transcription_available = not transcription_errors
        self._notes_available = not config_errors and bool(ollama_models)
        self._set_busy(False)

        self._log(
            "Transcription feature is available."
            if self._transcription_available
            else "Transcription feature unavailable due to missing dependencies."
        )
        self._log(
            "Note generation feature is available."
            if self._notes_available
            else "Note generation feature unavailable due to missing dependencies."
        )

        self._populate_selectors(ollama_models)

        if config_errors:
            self._log("Status: Error - Missing Dependencies")
            for error in config_errors:
                self._log(error)
            if transcription_errors:
                QMessageBox.critical(
                    self,
                    "Dependency Error",
                    "The application is missing required dependencies:\n\n"
                    + "\n".join(transcription_errors)
                    + "\n\nPlease follow the instructions above to download and set up the "
                    "required components.\n\n"
                    f"Visit {OLLAMA_DOWNLOAD_URL} to download and install Ollama, and keep it "
                    "running when using this application.\n\n"
                    "Read the README.md file in the project directory for more information.",
                )
        else:
            self._log("Status: Ready")
            self._log("All dependencies are met.")

        if ollama_warning:
            self._log(ollama_warning)

    def _fetch_ollama_models(self) -> Tuple[List[str], Optional[str]]:
        """Return the installed Ollama models and a warning to log, if any."""
        try:
            models = self._note_generator.get_available_models()
        except NoteGenerationError as exc:
            return [], f"WARNING: {exc} Note generation feature will be disabled."
        if not models:
            return [], (
                "WARNING: No Ollama models found. Note generation feature will be disabled. "
                "Please download and set up models using Ollama (e.g., run 'ollama pull llama2' "
                f"in terminal). Visit {OLLAMA_DOWNLOAD_URL} to download and install Ollama."
            )
        return models, None

    def _populate_selectors(self, ollama_models: List[str]) -> None:
        self.ollama_model_combo.clear()
        if ollama_models:
            self.ollama_model_combo.addItems(ollama_models)
        else:
            self.ollama_model_combo.addItem("Ollama not available", None)

        self.system_prompt_combo.clear()
        for prompt_path in self._config.prompt_paths:
            self.system_prompt_combo.addItem(prompt_path.name, prompt_path)

        self.model_bin_combo.clear()
        for model_path in self._config.model_paths:
            self.model_bin_combo.addItem(model_path.name, model_path)

    def _set_busy(self, busy: bool) -> None:
        """Lock inputs while a job runs; otherwise enable only the available features."""
        for widget in (
            self.select_audio_button,
            self.select_batch_button,
            self.ollama_model_combo,
            self.system_prompt_combo,
            self.model_bin_combo,
        ):
            widget.setEnabled(not busy)
        self.transcribe_button.setEnabled(not busy and self._transcription_available)
        self.make_notes_button.setEnabled(not busy and self._notes_available)

    def _select_audio_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Audio File", "", AUDIO_FILE_FILTER)
        if not file_name:
            return
        if not is_supported_audio_file(file_name):
            QMessageBox.warning(
                self,
                "Invalid File",
                "Selected file is not a supported audio format.\n"
                f"Supported formats: {SUPPORTED_FORMATS}",
            )
            return

        self._selected_files = [file_name]
        self._is_batch_selection = False
        self.audio_file_label.setText(f"Selected: {Path(file_name).name}")
        self._log(f"Selected audio file: {file_name}")

    def _select_batch_files(self) -> None:
        file_names, _ = QFileDialog.getOpenFileNames(self, "Open Audio Files", "", AUDIO_FILE_FILTER)
        if not file_names:
            return

        valid_files = [name for name in file_names if is_supported_audio_file(name)]
        skipped = len(file_names) - len(valid_files)
        if skipped:
            QMessageBox.warning(
                self,
                "Invalid Files",
                f"{skipped} file(s) were not supported audio formats and were skipped.\n"
                f"Supported formats: {SUPPORTED_FORMATS}",
            )
        if not valid_files:
            return

        self._selected_files = valid_files
        self._is_batch_selection = True
        self.audio_file_label.setText(f"Selected {len(valid_files)} files for batch processing")
        self._log(
            f"Selected {len(valid_files)} audio files for batch processing: "
            f"{[Path(name).name for name in valid_files]}"
        )

    def _start_job(self, kind: JobKind) -> None:
        """Validate the selections, confirm with the user, and start processing."""
        if not self._selected_files:
            QMessageBox.warning(
                self, "No Audio File", "Please select an audio file or multiple files first."
            )
            return

        model_path = self.model_bin_combo.currentData()
        prompt_path = self.system_prompt_combo.currentData()
        if model_path is None:
            QMessageBox.warning(
                self, "No Transcription Model", "Please select a transcription model first."
            )
            return
        if kind is JobKind.NOTES and prompt_path is None:
            QMessageBox.warning(self, "No System Prompt", "Please select a system prompt first.")
            return

        text = _JOB_TEXT[kind]
        files = tuple(self._selected_files)
        if self._is_batch_selection:
            title, question = text.confirm_batch_title, text.confirm_batch.format(count=len(files))
        else:
            title, question = text.confirm_title, text.confirm_single.format(name=Path(files[0]).name)
        reply = QMessageBox.question(self, title, question, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self._job = _JobSettings(
            kind=kind,
            files=files,
            is_batch=self._is_batch_selection,
            model_path=model_path,
            prompt_path=prompt_path,
            ollama_model=self.ollama_model_combo.currentText(),
        )
        self._job_index = 0
        self._set_busy(True)
        self.progress_bar.setValue(0)
        self._run_current_file()

    def _run_current_file(self) -> None:
        job = self._job
        if job is None:
            return
        if self._job_index >= len(job.files):
            self._log(_JOB_TEXT[job.kind].batch_done)
            self._finish_job()
            return

        audio_path = job.files[self._job_index]
        if job.is_batch:
            self._log(
                _JOB_TEXT[job.kind].batch_item.format(
                    index=self._job_index + 1, total=len(job.files), name=Path(audio_path).name
                )
            )

        worker = self._create_worker(job, audio_path)
        worker.progress.connect(self.progress_bar.setValue)
        worker.log.connect(self._log)
        worker.result_ready.connect(self._on_file_finished)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _create_worker(self, job: _JobSettings, audio_path: str) -> QThread:
        if job.kind is JobKind.NOTES:
            assert job.prompt_path is not None
            return NotesWorker(
                self._config.whisper_exe,
                job.model_path,
                audio_path,
                job.prompt_path,
                job.ollama_model,
                parent=self,
            )
        return TranscriptionWorker(self._config.whisper_exe, job.model_path, audio_path, parent=self)

    def _on_file_finished(self, result: Optional[JobResult]) -> None:
        job = self._job
        if job is None:
            return
        self.progress_bar.setValue(100)
        audio_path = job.files[self._job_index]
        text = _JOB_TEXT[job.kind]

        if not job.is_batch:
            self._finish_job()
            if result is None:
                QMessageBox.critical(self, text.failed_title, text.failed_message)
            else:
                self._save_result(job.kind, result, audio_path, show_summary=True)
            return

        if result is None:
            self._log(
                text.batch_item_failed.format(index=self._job_index + 1, name=Path(audio_path).name)
            )
        else:
            self._save_result(job.kind, result, audio_path, show_summary=False)
        self._job_index += 1
        self._run_current_file()

    def _finish_job(self) -> None:
        self._job = None
        self._worker = None
        self._set_busy(False)

    def _save_result(
        self, kind: JobKind, result: JobResult, audio_path: str, show_summary: bool
    ) -> None:
        """Write the job's output files, stopping at the first failure."""
        paths = OutputPaths.for_audio(audio_path, self._config.output_dir)
        saved = [f"- {paths.transcript} (Transcript)"]
        if not self._save_step(
            "Transcript", "transcript", paths.transcript,
            lambda: write_text(paths.transcript, result.transcript),
        ):
            return

        if result.notes is not None:
            notes = result.notes
            if not self._save_step(
                "Markdown notes", "markdown notes", paths.notes_markdown,
                lambda: write_text(paths.notes_markdown, notes),
            ):
                return
            if not self._save_step(
                "PDF notes", "PDF", paths.notes_pdf, lambda: write_pdf(paths.notes_pdf, notes)
            ):
                return
            saved += [
                f"- {paths.notes_markdown} (Markdown Notes)",
                f"- {paths.notes_pdf} (PDF Notes)",
            ]

        self._log(_JOB_TEXT[kind].succeeded.format(name=Path(audio_path).name))
        if show_summary:
            if result.notes is None:
                summary = "Audio transcription completed successfully!\n\nFile saved to:\n"
            else:
                summary = (
                    "Meeting notes and transcript have been generated successfully!\n\n"
                    "Files saved to:\n"
                )
            QMessageBox.information(self, "Success", summary + "\n".join(saved))

    def _save_step(
        self, saved_label: str, error_label: str, path: Path, action: Callable[[], None]
    ) -> bool:
        """Run one save action, reporting success or failure; return whether it succeeded."""
        try:
            action()
        except ImportError:
            install_hint = "Cannot save PDF. Install with 'pip install reportlab'"
            self._log(f"PDF library missing. {install_hint}")
            QMessageBox.warning(
                self, "PDF Library Missing", f"reportlab library not found. {install_hint}"
            )
            return False
        except Exception as exc:  # Report any write/render failure to the user.
            self._log(f"Error saving {error_label}: {exc}")
            QMessageBox.critical(self, "Save Error", f"Failed to save {error_label}: {exc}")
            return False
        self._log(f"{saved_label} saved to {path}")
        return True
