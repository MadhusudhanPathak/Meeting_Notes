"""Main application window: selections, job orchestration, and result saving."""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PyQt5.QtCore import QThread, QTimer, QUrl, Qt
from PyQt5.QtGui import QCloseEvent, QDesktopServices, QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from meeting_notes.config import APP_NAME, AppConfig
from meeting_notes.core.control import JobControl
from meeting_notes.core.languages import DEFAULT_LANGUAGE, WHISPER_LANGUAGES
from meeting_notes.core.note_generator import OLLAMA_DOWNLOAD_URL, NoteGenerator
from meeting_notes.core.transcriber import (
    AUDIO_EXTENSIONS,
    MEDIA_EXTENSIONS,
    VIDEO_EXTENSIONS,
    TranscriptionOptions,
    is_supported_media_file,
)
from meeting_notes.export.writer import OutputPaths, write_pdf, write_text
from meeting_notes.ui import styles
from meeting_notes.ui.download_dialog import DownloadDialog
from meeting_notes.ui.preferences import Keys, Preferences
from meeting_notes.ui.workers import (
    BUSY,
    DependencyCheckWorker,
    DependencyReport,
    JobRequest,
    JobResult,
    NotesWorker,
    TranscriptionWorker,
    format_clock,
)

MEDIA_FILE_FILTER = "Audio and Video Files ({});;Audio Files ({});;Video Files ({})".format(
    *(" ".join(f"*{ext}" for ext in group)
      for group in (MEDIA_EXTENSIONS, AUDIO_EXTENSIONS, VIDEO_EXTENSIONS))
)
SUPPORTED_FORMATS = ", ".join(ext.lstrip(".").upper() for ext in MEDIA_EXTENSIONS)
NO_FILE_TEXT = "No file selected - choose files or drag and drop them here"
AUTOMATIC_GPU_LABEL = "Automatic"
_URL_PATTERN = re.compile(r"(https?://[^\s<>\"')]+)")


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
            "This will transcribe {count} files sequentially using the selected model."
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
            "This will process {count} files sequentially using the selected model and "
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


@dataclass
class _ActiveJob:
    """Selections captured when a job starts, plus its progress through the file list."""

    kind: JobKind
    files: Tuple[str, ...]
    is_batch: bool
    control: JobControl
    model_path: Path
    prompt_path: Optional[Path]
    ollama_model: str
    options: TranscriptionOptions
    include_timestamps: bool
    save_subtitles: bool
    index: int = 0

    def request(self, whisper_exe: Path, ffmpeg: Optional[Path]) -> JobRequest:
        return JobRequest(
            whisper_exe=whisper_exe,
            ffmpeg=ffmpeg,
            model_path=self.model_path,
            media_path=self.files[self.index],
            options=self.options,
            include_timestamps=self.include_timestamps,
            save_subtitles=self.save_subtitles,
            prompt_path=self.prompt_path,
            ollama_model=self.ollama_model,
        )


class MainWindow(QMainWindow):
    """Top-level window that drives single-file and batch processing."""

    def __init__(
        self,
        root: Path,
        note_generator: Optional[NoteGenerator] = None,
        preferences: Optional[Preferences] = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 60, 960, 860)
        self.setAcceptDrops(True)

        self._root = root
        self._note_generator = note_generator or NoteGenerator()
        self._prefs = preferences or Preferences()
        self._config: Optional[AppConfig] = None
        self._ollama_models: List[str] = []
        self._selected_files: List[str] = []
        self._is_batch_selection = False
        self._job: Optional[_ActiveJob] = None
        self._worker: Optional[QThread] = None
        self._checker: Optional[DependencyCheckWorker] = None
        self._transcription_available = False
        self._notes_available = False
        self._status_text = ""
        self._job_started = 0.0

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._refresh_status_label)

        self._build_ui()
        geometry = self._prefs.geometry()
        if geometry is not None:
            self.restoreGeometry(geometry)
        QTimer.singleShot(0, lambda: self._start_dependency_check(initial=True))

    # ----- layout -------------------------------------------------------------------

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
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(styles.STATUS_LABEL)
        progress_layout.addWidget(self.status_label)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_view = QTextBrowser()
        self.log_view.setOpenLinks(False)
        self.log_view.setAcceptDrops(False)
        self.log_view.anchorClicked.connect(QDesktopServices.openUrl)
        self.log_view.setMinimumHeight(170)
        log_layout.addWidget(self.log_view)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group, 1)

    def _build_controls(self) -> QGroupBox:
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()

        file_row = QHBoxLayout()
        self.audio_file_label = QLabel(NO_FILE_TEXT)
        self.audio_file_label.setWordWrap(True)
        self.audio_file_label.setStyleSheet(styles.FILE_LABEL)
        self.select_audio_button = QPushButton("Select Audio/Video File")
        self.select_audio_button.clicked.connect(self._select_audio_file)
        self.select_batch_button = QPushButton("Select Multiple Files")
        self.select_batch_button.clicked.connect(self._select_batch_files)
        file_row.addWidget(self.audio_file_label, 1)
        file_row.addWidget(self.select_audio_button)
        file_row.addWidget(self.select_batch_button)
        controls_layout.addLayout(file_row)

        self.ollama_model_combo = QComboBox()
        self.system_prompt_combo = QComboBox()
        self.model_bin_combo = QComboBox()
        self.language_combo = QComboBox()
        for code, name in WHISPER_LANGUAGES:
            self.language_combo.addItem(f"{name} ({code})", code)
        self.translate_checkbox = QCheckBox("Translate to English")
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItem(AUTOMATIC_GPU_LABEL, "")
        self.timestamps_checkbox = QCheckBox("Include timestamps in transcript")
        self.subtitles_checkbox = QCheckBox("Save subtitles (SRT and VTT)")
        self._restore_options()

        form = QGridLayout()
        form.setColumnStretch(1, 1)
        language_row = QHBoxLayout()
        language_row.addWidget(self.language_combo, 1)
        language_row.addWidget(self.translate_checkbox)
        options_row = QHBoxLayout()
        options_row.addWidget(self.timestamps_checkbox)
        options_row.addWidget(self.subtitles_checkbox)
        options_row.addStretch(1)
        rows = (
            ("Ollama Model:", self.ollama_model_combo),
            ("System Prompt:", self.system_prompt_combo),
            ("Transcription Model:", self.model_bin_combo),
            ("Spoken Language:", language_row),
            ("Graphics Card:", self.gpu_combo),
            ("Transcript Options:", options_row),
        )
        for row, (label, field) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            if isinstance(field, QHBoxLayout):
                form.addLayout(field, row, 1)
            else:
                form.addWidget(field, row, 1)
        controls_layout.addLayout(form)

        for combo, key in (
            (self.ollama_model_combo, Keys.OLLAMA_MODEL),
            (self.system_prompt_combo, Keys.SYSTEM_PROMPT),
            (self.model_bin_combo, Keys.WHISPER_MODEL),
        ):
            combo.currentTextChanged.connect(lambda text, key=key: self._prefs.set(key, text))
        self.language_combo.currentIndexChanged.connect(
            lambda: self._prefs.set(Keys.LANGUAGE, self.language_combo.currentData())
        )
        self.gpu_combo.currentIndexChanged.connect(
            lambda: self._prefs.set(Keys.GPU, self.gpu_combo.currentData() or "")
        )
        for checkbox, key in (
            (self.translate_checkbox, Keys.TRANSLATE),
            (self.timestamps_checkbox, Keys.TIMESTAMPS),
            (self.subtitles_checkbox, Keys.SUBTITLES),
        ):
            checkbox.toggled.connect(lambda checked, key=key: self._prefs.set(key, checked))

        buttons_layout = QHBoxLayout()
        self.transcribe_button = QPushButton("Transcribe Audio")
        self.transcribe_button.setObjectName("generateButton")
        self.transcribe_button.setStyleSheet(styles.TRANSCRIBE_BUTTON)
        self.transcribe_button.clicked.connect(lambda: self._start_job(JobKind.TRANSCRIBE))
        buttons_layout.addWidget(self.transcribe_button, 1)
        self.make_notes_button = QPushButton("Generate Meeting Notes")
        self.make_notes_button.setObjectName("generateButton")
        self.make_notes_button.setStyleSheet(styles.GENERATE_BUTTON)
        self.make_notes_button.clicked.connect(lambda: self._start_job(JobKind.NOTES))
        buttons_layout.addWidget(self.make_notes_button, 4)
        controls_layout.addLayout(buttons_layout)

        actions_layout = QHBoxLayout()
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._toggle_pause)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_job)
        self.open_output_button = QPushButton("Open Output Folder")
        self.open_output_button.clicked.connect(self._open_output_folder)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setToolTip(
            "Re-check Whisper, models, prompts, Ollama, and graphics cards"
        )
        self.refresh_button.clicked.connect(lambda: self._start_dependency_check(initial=False))
        self.download_button = QPushButton("Download Models")
        self.download_button.clicked.connect(self._open_download_dialog)
        for button in (self.pause_button, self.cancel_button):
            actions_layout.addWidget(button)
        actions_layout.addStretch(1)
        for button in (self.open_output_button, self.refresh_button, self.download_button):
            actions_layout.addWidget(button)
        controls_layout.addLayout(actions_layout)

        controls_group.setLayout(controls_layout)
        self._update_controls()
        return controls_group

    def _restore_options(self) -> None:
        _select_data(self.language_combo, self._prefs.text(Keys.LANGUAGE, DEFAULT_LANGUAGE))
        self.translate_checkbox.setChecked(self._prefs.flag(Keys.TRANSLATE, False))
        self.timestamps_checkbox.setChecked(self._prefs.flag(Keys.TIMESTAMPS, True))
        self.subtitles_checkbox.setChecked(self._prefs.flag(Keys.SUBTITLES, False))

    # ----- logging and status -------------------------------------------------------

    def _log(self, message: str) -> None:
        escaped = html.escape(message)
        linked = _URL_PATTERN.sub(r'<a href="\1">\1</a>', escaped)
        self.log_view.append(f'<span style="white-space: pre-wrap;">{linked}</span>')

    def _log_saved(self, label: str, path: Path) -> None:
        url = QUrl.fromLocalFile(str(path)).toString()
        self.log_view.append(
            f"{html.escape(label)} saved to <a href=\"{html.escape(url)}\">"
            f"{html.escape(str(path))}</a>"
        )

    def _set_status(self, text: str) -> None:
        self._status_text = text
        self._refresh_status_label()

    def _refresh_status_label(self) -> None:
        text = self._status_text
        if self._job is not None:
            if self._job.control.is_paused:
                text = f"Paused - {text}" if text else "Paused"
            elapsed = format_clock(time.monotonic() - self._job_started)
            text = f"{text}   (elapsed {elapsed})" if text else f"Elapsed {elapsed}"
        self.status_label.setText(text)

    def _set_progress(self, value: int) -> None:
        if value == BUSY:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(value)

    # ----- dependency check ---------------------------------------------------------

    def _start_dependency_check(self, initial: bool) -> None:
        if self._checker is not None or self._job is not None:
            return
        self._log("Status: Checking dependencies...")
        self._set_status("Checking dependencies...")
        self._set_progress(BUSY)
        checker = DependencyCheckWorker(self._root, self._note_generator, parent=self)
        checker.report_ready.connect(lambda report: self._on_dependencies_checked(report, initial))
        checker.finished.connect(checker.deleteLater)
        self._checker = checker
        self._update_controls()
        checker.start()

    def _on_dependencies_checked(self, report: DependencyReport, initial: bool) -> None:
        self._checker = None
        self._config = report.config
        self._ollama_models = report.ollama_models
        config_errors = report.config.validate()
        transcription_errors = report.config.transcription_errors()

        self._transcription_available = not transcription_errors
        self._notes_available = not config_errors and bool(report.ollama_models)
        self._populate_selectors(report)
        self._set_progress(0)
        self._set_status("")
        self._update_controls()

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
        if report.gpu_adapters:
            self._log(f"Graphics cards found: {', '.join(report.gpu_adapters)}")

        if config_errors:
            self._log("Status: Error - Missing Dependencies")
            for error in config_errors:
                self._log(error)
            if transcription_errors and initial:
                QMessageBox.critical(
                    self,
                    "Dependency Error",
                    "The application is missing required dependencies:\n\n"
                    + "\n".join(transcription_errors)
                    + "\n\nUse 'Download Models' to get a transcription model, or follow the "
                    "instructions above to set up the required components, then click "
                    "'Refresh'.\n\n"
                    f"Visit {OLLAMA_DOWNLOAD_URL} to download and install Ollama, and keep it "
                    "running when using this application.\n\n"
                    "Read the README.md file in the project directory for more information.",
                )
        else:
            self._log("Status: Ready")
            self._log("All dependencies are met.")

        for warning in report.config.warnings():
            self._log(warning)
        if report.ollama_warning:
            self._log(report.ollama_warning)

    def _populate_selectors(self, report: DependencyReport) -> None:
        config = report.config
        combos = (
            self.ollama_model_combo, self.system_prompt_combo, self.model_bin_combo, self.gpu_combo
        )
        for combo in combos:
            combo.blockSignals(True)
            combo.clear()

        if report.ollama_models:
            self.ollama_model_combo.addItems(report.ollama_models)
        else:
            self.ollama_model_combo.addItem("Ollama not available", None)
        for prompt_path in config.prompt_paths:
            label = (
                f"{prompt_path.stem} (built-in)"
                if config.is_builtin_prompt(prompt_path)
                else prompt_path.name
            )
            self.system_prompt_combo.addItem(label, prompt_path)
        for model_path in config.model_paths:
            self.model_bin_combo.addItem(model_path.name, model_path)
        self.gpu_combo.addItem(AUTOMATIC_GPU_LABEL, "")
        for adapter in report.gpu_adapters:
            self.gpu_combo.addItem(adapter, adapter)

        _select_text(self.ollama_model_combo, self._prefs.text(Keys.OLLAMA_MODEL))
        _select_text(self.system_prompt_combo, self._prefs.text(Keys.SYSTEM_PROMPT))
        _select_text(self.model_bin_combo, self._prefs.text(Keys.WHISPER_MODEL))
        _select_data(self.gpu_combo, self._prefs.text(Keys.GPU))
        for combo in combos:
            combo.blockSignals(False)

    def _update_controls(self) -> None:
        busy = self._job is not None
        idle = not busy and self._checker is None
        for widget in (
            self.select_audio_button, self.select_batch_button, self.ollama_model_combo,
            self.system_prompt_combo, self.model_bin_combo, self.language_combo,
            self.translate_checkbox, self.gpu_combo, self.timestamps_checkbox,
            self.subtitles_checkbox, self.refresh_button,
        ):
            widget.setEnabled(idle)
        self.download_button.setEnabled(idle and self._config is not None)
        self.transcribe_button.setEnabled(idle and self._transcription_available)
        self.make_notes_button.setEnabled(idle and self._notes_available)
        cancelling = busy and self._job is not None and self._job.control.is_cancelled
        self.pause_button.setEnabled(busy and not cancelling)
        self.cancel_button.setEnabled(busy and not cancelling)
        self.pause_button.setText("Resume" if busy and self._job.control.is_paused else "Pause")

    # ----- file selection -----------------------------------------------------------

    def _select_audio_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Audio or Video File", self._prefs.text(Keys.LAST_DIRECTORY),
            MEDIA_FILE_FILTER,
        )
        if not file_name:
            return
        if not is_supported_media_file(file_name):
            QMessageBox.warning(
                self,
                "Invalid File",
                "Selected file is not a supported audio or video format.\n"
                f"Supported formats: {SUPPORTED_FORMATS}",
            )
            return
        self._set_selection([file_name], batch=False)

    def _select_batch_files(self) -> None:
        file_names, _ = QFileDialog.getOpenFileNames(
            self, "Open Audio or Video Files", self._prefs.text(Keys.LAST_DIRECTORY),
            MEDIA_FILE_FILTER,
        )
        if file_names:
            self._accept_files(file_names, batch=True)

    def _accept_files(self, file_names: List[str], batch: bool) -> None:
        valid_files = [name for name in file_names if is_supported_media_file(name)]
        skipped = len(file_names) - len(valid_files)
        if skipped:
            QMessageBox.warning(
                self,
                "Invalid Files",
                f"{skipped} file(s) were not supported audio or video formats and were skipped.\n"
                f"Supported formats: {SUPPORTED_FORMATS}",
            )
        if valid_files:
            self._set_selection(valid_files, batch=batch or len(valid_files) > 1)

    def _set_selection(self, files: List[str], batch: bool) -> None:
        self._selected_files = files
        self._is_batch_selection = batch
        if batch:
            self.audio_file_label.setText(f"Selected {len(files)} files for batch processing")
            self._log(
                f"Selected {len(files)} files for batch processing: "
                f"{[Path(name).name for name in files]}"
            )
        else:
            self.audio_file_label.setText(f"Selected: {Path(files[0]).name}")
            self._log(f"Selected audio file: {files[0]}")
        self._prefs.set(Keys.LAST_DIRECTORY, str(Path(files[0]).parent))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._job is None and any(
            url.isLocalFile() and is_supported_media_file(url.toLocalFile())
            for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        files = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if self._job is None and files:
            event.acceptProposedAction()
            self._accept_files(files, batch=False)

    # ----- running jobs -------------------------------------------------------------

    def _start_job(self, kind: JobKind) -> None:
        """Validate the selections, confirm with the user, and start processing."""
        if self._config is None or self._job is not None:
            return
        if not self._selected_files:
            QMessageBox.warning(
                self, "No Audio File", "Please select an audio or video file first."
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
            title = text.confirm_title
            question = text.confirm_single.format(name=Path(files[0]).name)
        reply = QMessageBox.question(self, title, question, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self._job = _ActiveJob(
            kind=kind,
            files=files,
            is_batch=self._is_batch_selection,
            control=JobControl(),
            model_path=model_path,
            prompt_path=prompt_path if kind is JobKind.NOTES else None,
            ollama_model=self.ollama_model_combo.currentText(),
            options=TranscriptionOptions(
                language=self.language_combo.currentData() or DEFAULT_LANGUAGE,
                translate=self.translate_checkbox.isChecked(),
                gpu=self.gpu_combo.currentData() or None,
            ),
            include_timestamps=self.timestamps_checkbox.isChecked(),
            save_subtitles=self.subtitles_checkbox.isChecked(),
        )
        self._job_started = time.monotonic()
        self._elapsed_timer.start()
        self._set_progress(0)
        self._update_controls()
        self._run_current_file()

    def _run_current_file(self) -> None:
        job = self._job
        if job is None or self._config is None:
            return
        if job.index >= len(job.files):
            self._log(_JOB_TEXT[job.kind].batch_done)
            self._finish_job()
            return

        media_path = job.files[job.index]
        if job.is_batch:
            self._log(
                _JOB_TEXT[job.kind].batch_item.format(
                    index=job.index + 1, total=len(job.files), name=Path(media_path).name
                )
            )
        worker_class = NotesWorker if job.kind is JobKind.NOTES else TranscriptionWorker
        whisper_exe = self._config.whisper_exe
        if whisper_exe is None:
            self._log("Transcription engine not found. Click 'Refresh' after installing it.")
            self._finish_job()
            return
        request = job.request(whisper_exe, self._config.ffmpeg)
        worker = worker_class(request, job.control, parent=self)
        worker.progress.connect(self._set_progress)
        worker.status.connect(self._set_status)
        worker.log.connect(self._log)
        worker.result_ready.connect(self._on_file_finished)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _on_file_finished(self, result: Optional[JobResult]) -> None:
        job = self._job
        if job is None:
            return
        media_path = job.files[job.index]
        text = _JOB_TEXT[job.kind]

        if job.control.is_cancelled:
            if job.is_batch:
                self._log(f"Batch cancelled after {job.index} of {len(job.files)} files.")
            self._finish_job()
            self._set_progress(0)
            return

        self._set_progress(100)
        if not job.is_batch:
            self._finish_job()
            if result is None:
                QMessageBox.critical(self, text.failed_title, text.failed_message)
            else:
                self._save_result(job.kind, result, media_path, show_summary=True)
            return

        if result is None:
            self._log(
                text.batch_item_failed.format(index=job.index + 1, name=Path(media_path).name)
            )
        else:
            self._save_result(job.kind, result, media_path, show_summary=False)
        job.index += 1
        self._run_current_file()

    def _finish_job(self) -> None:
        self._job = None
        self._worker = None
        self._elapsed_timer.stop()
        self._set_status("")
        self._update_controls()

    def _toggle_pause(self) -> None:
        job = self._job
        if job is None:
            return
        if job.control.is_paused:
            job.control.resume()
            self._log("Resumed.")
        else:
            job.control.pause()
            self._log("Paused.")
        self._refresh_status_label()
        self._update_controls()

    def _cancel_job(self) -> None:
        job = self._job
        if job is None or job.control.is_cancelled:
            return
        self._log("Cancelling...")
        job.control.cancel()
        self._set_status("Cancelling...")
        self._update_controls()

    # ----- saving results -----------------------------------------------------------

    def _save_result(
        self, kind: JobKind, result: JobResult, media_path: str, show_summary: bool
    ) -> None:
        """Write the job's output files, stopping at the first failure."""
        assert self._config is not None
        paths = OutputPaths.for_media(media_path, self._config.output_dir)
        saved: List[Tuple[str, Path]] = []
        steps: List[Tuple[str, str, Path, Callable[[], None]]] = [
            ("Transcript", "transcript", paths.transcript,
             lambda: write_text(paths.transcript, result.transcript)),
        ]
        if result.srt is not None and result.vtt is not None:
            srt, vtt = result.srt, result.vtt
            steps += [
                ("Subtitles (SRT)", "SRT subtitles", paths.subtitles_srt,
                 lambda: write_text(paths.subtitles_srt, srt)),
                ("Subtitles (VTT)", "VTT subtitles", paths.subtitles_vtt,
                 lambda: write_text(paths.subtitles_vtt, vtt)),
            ]
        if result.notes is not None:
            notes = result.notes
            subtitle = f"{Path(media_path).name} - {datetime.now():%d %b %Y}"
            steps += [
                ("Markdown notes", "markdown notes", paths.notes_markdown,
                 lambda: write_text(paths.notes_markdown, notes)),
                ("PDF notes", "PDF", paths.notes_pdf,
                 lambda: write_pdf(paths.notes_pdf, notes, subtitle)),
            ]

        for saved_label, error_label, path, action in steps:
            if not self._save_step(saved_label, error_label, path, action):
                return
            saved.append((saved_label, path))

        self._log(_JOB_TEXT[kind].succeeded.format(name=Path(media_path).name))
        if show_summary:
            self._show_success(result.notes is not None, saved)

    def _save_step(
        self, saved_label: str, error_label: str, path: Path, action: Callable[[], None]
    ) -> bool:
        """Run one save action, reporting success or failure; return whether it succeeded."""
        try:
            action()
        except Exception as exc:  # Report any write/render failure to the user.
            self._log(f"Error saving {error_label}: {exc}")
            QMessageBox.critical(self, "Save Error", f"Failed to save {error_label}: {exc}")
            return False
        self._log_saved(saved_label, path)
        return True

    def _show_success(self, with_notes: bool, saved: List[Tuple[str, Path]]) -> None:
        heading = (
            "Meeting notes and transcript have been generated successfully!"
            if with_notes
            else "Audio transcription completed successfully!"
        )
        links = "".join(
            f'<li><a href="{html.escape(QUrl.fromLocalFile(str(path)).toString())}">'
            f"{html.escape(path.name)}</a> ({html.escape(label)})</li>"
            for label, path in saved
        )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Success")
        box.setTextFormat(Qt.RichText)
        box.setText(f"{heading}<br><br>Files saved (click to open):<ul>{links}</ul>")
        for label in box.findChildren(QLabel):
            label.setOpenExternalLinks(True)
        open_folder: QAbstractButton = box.addButton("Open Output Folder", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Ok)
        box.exec_()
        if box.clickedButton() is open_folder:
            self._open_output_folder()

    # ----- tools --------------------------------------------------------------------

    def _open_output_folder(self) -> None:
        output_dir = self._config.output_dir if self._config else self._root / "output"
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Output Folder", f"Could not create {output_dir}: {exc}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_dir)))

    def _open_download_dialog(self) -> None:
        if self._config is None:
            return
        dialog = DownloadDialog(
            self._config.input_dir,
            (path.name for path in self._config.model_paths),
            self._ollama_models,
            parent=self,
        )
        dialog.exec_()
        if dialog.downloaded_any:
            self._start_dependency_check(initial=False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._job is not None:
            reply = QMessageBox.question(
                self, "Job Running", "A job is still running. Cancel it and exit?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self._job.control.cancel()
            if self._worker is not None:
                self._worker.wait()
        if self._checker is not None:
            self._checker.wait()
        self._prefs.set(Keys.GEOMETRY, self.saveGeometry())
        super().closeEvent(event)


def _select_text(combo: QComboBox, text: str) -> None:
    index = combo.findText(text) if text else -1
    if index >= 0:
        combo.setCurrentIndex(index)


def _select_data(combo: QComboBox, value: str) -> None:
    for index in range(combo.count()):
        if (combo.itemData(index) or "") == value:
            combo.setCurrentIndex(index)
            return
