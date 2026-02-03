

import os
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QFileDialog, QProgressBar, QTextEdit
from PyQt5.QtCore import QThread, pyqtSignal
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from config import Config
from note_generator import NoteGenerator
from transcriber import Transcriber
import utils

class Worker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(self, config, selected_audio_file, system_prompt_path, ollama_model):
        super().__init__()
        self.config = config
        self.selected_audio_file = selected_audio_file
        self.system_prompt_path = system_prompt_path
        self.ollama_model = ollama_model

    def run(self):
        try:
            self.log.emit("Starting meeting notes generation...")
            
            # 1. Transcription
            self.log.emit("Transcribing audio...")
            self.progress.emit(10)
            transcriber = Transcriber(self.config.main_exe_path, self.config.model_path)
            transcript = transcriber.transcribe(self.selected_audio_file)
            self.log.emit("Transcription complete.")
            self.progress.emit(50)

            # 2. Note Generation
            self.log.emit("Generating notes...")
            system_prompt = self.config.get_system_prompt(self.system_prompt_path)
            note_generator = NoteGenerator()
            notes = note_generator.generate_notes(transcript, system_prompt, self.ollama_model)
            self.log.emit("Note generation complete.")
            self.progress.emit(90)

            self.finished.emit({"notes": notes, "transcript": transcript})

        except Exception as e:
            self.log.emit(f"An error occurred: {e}")
            self.finished.emit(None)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local Meeting Notes")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.status_label = QLabel("Status: Initializing...")
        self.layout.addWidget(self.status_label)

        self.select_audio_button = QPushButton("Select Audio File")
        self.select_audio_button.clicked.connect(self.select_audio_file)
        self.layout.addWidget(self.select_audio_button)

        self.ollama_model_combo = QComboBox()
        self.layout.addWidget(self.ollama_model_combo)

        self.system_prompt_combo = QComboBox()
        self.layout.addWidget(self.system_prompt_combo)

        self.make_notes_button = QPushButton("Make meeting notes")
        self.make_notes_button.setEnabled(False)
        self.make_notes_button.clicked.connect(self.generate_notes)
        self.layout.addWidget(self.make_notes_button)

        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)

        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.layout.addWidget(self.log_text_edit)

        self.config = Config()
        self.note_generator = NoteGenerator()
        self.check_dependencies()
        self.selected_audio_file = None
        self.worker = None

    def check_dependencies(self):
        self.log_text_edit.append("Checking dependencies...")
        errors = self.config.validate()
        ollama_models = self.note_generator.get_available_models()

        if not ollama_models:
            errors.append("Ollama is not running or not accessible.")

        if errors:
            self.status_label.setText("Status: Error!")
            for error in errors:
                self.log_text_edit.append(f"- {error}")
            self.make_notes_button.setEnabled(False)
        else:
            self.status_label.setText("Status: Ready")
            self.log_text_edit.append("All dependencies are met.")
            self.ollama_model_combo.addItems(ollama_models)
            for prompt_path in self.config.system_prompt_paths:
                self.system_prompt_combo.addItem(os.path.basename(prompt_path), prompt_path)

    def select_audio_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Audio File", "", "Audio Files (*.mp3 *.wav)")
        if file_name:
            self.selected_audio_file = file_name
            self.log_text_edit.append(f"Selected audio file: {self.selected_audio_file}")
            self.make_notes_button.setEnabled(True)

    def generate_notes(self):
        if not self.selected_audio_file:
            self.log_text_edit.append("Please select an audio file first.")
            return

        self.make_notes_button.setEnabled(False)
        self.progress_bar.setValue(0)

        system_prompt_path = self.system_prompt_combo.currentData()
        ollama_model = self.ollama_model_combo.currentText()

        self.worker = Worker(self.config, self.selected_audio_file, system_prompt_path, ollama_model)
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.update_log)
        self.worker.finished.connect(self.generation_finished)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_log(self, message):
        self.log_text_edit.append(message)

    def generation_finished(self, result):
        self.progress_bar.setValue(100)
        self.make_notes_button.setEnabled(True)
        if result:
            self.save_files(result["notes"], result["transcript"])

    def save_files(self, notes, transcript):
        base_name = os.path.splitext(os.path.basename(self.selected_audio_file))[0]
        timestamped_base_name = utils.get_timestamped_filename(base_name, "")[:-1]

        # Save transcript
        txt_file_name, _ = QFileDialog.getSaveFileName(self, "Save Transcript", f"{timestamped_base_name}.txt", "Text Files (*.txt)")
        if txt_file_name:
            with open(txt_file_name, "w", encoding="utf-8") as f:
                f.write(transcript)
            self.log_text_edit.append(f"Transcript saved to {txt_file_name}")

        # Save notes as PDF
        pdf_file_name, _ = QFileDialog.getSaveFileName(self, "Save Notes", f"{timestamped_base_name}.pdf", "PDF Files (*.pdf)")
        if pdf_file_name:
            doc = SimpleDocTemplate(pdf_file_name)
            styles = getSampleStyleSheet()
            story = [Paragraph(line.replace('\n', '<br/>')) for line in notes.split('\n')]
            doc.build(story)
            self.log_text_edit.append(f"Notes saved to {pdf_file_name}")

