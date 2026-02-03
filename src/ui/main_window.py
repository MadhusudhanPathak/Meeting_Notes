"""
Main UI module for the Local Meeting Notes application.
Contains the main window and GUI components.
"""

import os
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QComboBox, QFileDialog, QProgressBar, QTextEdit, 
    QMessageBox, QGroupBox
)
from PyQt5.QtCore import QThread

from src.config.settings import ConfigManager
from src.core.note_generator import NoteGenerator, NoteGenerationError
from src.workers.processing_worker import ProcessingWorker
from src.utils.helpers import get_timestamped_filename, validate_audio_file


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("Local Meeting Notes Generator")
        self.setGeometry(100, 100, 900, 700)
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.note_generator = NoteGenerator()
        self.selected_audio_file: Optional[str] = None
        self.worker: Optional[QThread] = None
        
        # Setup UI
        self.setup_ui()
        self.check_dependencies()
    
    def setup_ui(self) -> None:
        """Setup the user interface components."""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Title label
        title_label = QLabel("Local Meeting Notes Generator")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # Status group
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Status: Initializing...")
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        # Audio file selection
        audio_layout = QHBoxLayout()
        self.select_audio_button = QPushButton("Select Audio File")
        self.select_audio_button.clicked.connect(self.select_audio_file)
        self.audio_file_label = QLabel("No file selected")
        audio_layout.addWidget(self.select_audio_button)
        audio_layout.addWidget(self.audio_file_label)
        controls_layout.addLayout(audio_layout)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Ollama Model:"))
        self.ollama_model_combo = QComboBox()
        model_layout.addWidget(self.ollama_model_combo)
        controls_layout.addLayout(model_layout)
        
        # System prompt selection
        prompt_layout = QHBoxLayout()
        prompt_layout.addWidget(QLabel("System Prompt:"))
        self.system_prompt_combo = QComboBox()
        prompt_layout.addWidget(self.system_prompt_combo)
        controls_layout.addLayout(prompt_layout)
        
        # Process button
        self.make_notes_button = QPushButton("Generate Meeting Notes")
        self.make_notes_button.setEnabled(False)
        self.make_notes_button.clicked.connect(self.generate_notes)
        controls_layout.addWidget(self.make_notes_button)
        
        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # Log section
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        log_layout.addWidget(self.log_text_edit)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
    
    def check_dependencies(self) -> None:
        """Check for required dependencies and update UI accordingly."""
        self.log_text_edit.append("Checking dependencies...")
        config_errors = self.config_manager.validate()
        
        try:
            ollama_models = self.note_generator.get_available_models()
        except NoteGenerationError as e:
            ollama_models = []
            config_errors.append(str(e))
        
        if config_errors:
            self.status_label.setText("Status: Error - Missing Dependencies")
            for error in config_errors:
                self.log_text_edit.append(f"- {error}")
            self.make_notes_button.setEnabled(False)
            
            # Show error dialog
            error_msg = "\n".join(config_errors)
            QMessageBox.critical(
                self, 
                "Dependency Error", 
                f"The application is missing required dependencies:\n\n{error_msg}\n\n"
                "Please ensure all required files are in the 'input' directory and Ollama is running."
            )
        else:
            self.status_label.setText("Status: Ready")
            self.log_text_edit.append("All dependencies are met.")
            
            # Populate model combo
            self.ollama_model_combo.clear()
            self.ollama_model_combo.addItems(ollama_models)
            
            # Populate system prompt combo
            self.system_prompt_combo.clear()
            for prompt_path in self.config_manager.app_config.system_prompt_paths:
                self.system_prompt_combo.addItem(
                    os.path.basename(prompt_path), 
                    prompt_path
                )
    
    def select_audio_file(self) -> None:
        """Handle audio file selection."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Open Audio File", 
            "", 
            "Audio Files (*.mp3 *.wav *.m4a *.flac *.aac *.ogg)"
        )
        
        if file_name:
            # Validate the selected file
            if not validate_audio_file(file_name):
                QMessageBox.warning(
                    self,
                    "Invalid File",
                    "Selected file is not a supported audio format.\nSupported formats: MP3, WAV, M4A, FLAC, AAC, OGG"
                )
                return
            
            self.selected_audio_file = file_name
            self.audio_file_label.setText(f"Selected: {os.path.basename(file_name)}")
            self.log_text_edit.append(f"Selected audio file: {file_name}")
            self.make_notes_button.setEnabled(True)
    
    def generate_notes(self) -> None:
        """Start the note generation process."""
        if not self.selected_audio_file:
            QMessageBox.warning(
                self,
                "No Audio File",
                "Please select an audio file first."
            )
            return
        
        # Confirm overwrite if files exist
        base_name = Path(self.selected_audio_file).stem
        timestamped_base_name = get_timestamped_filename(base_name, "")
        # Remove the trailing dot from timestamped filename
        timestamped_base_name = timestamped_base_name[:-1] if timestamped_base_name.endswith('.') else timestamped_base_name
        
        reply = QMessageBox.question(
            self,
            "Confirm Processing",
            f"This will process '{os.path.basename(self.selected_audio_file)}' and "
            f"generate notes using the selected model and prompt.\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Disable UI during processing
        self.make_notes_button.setEnabled(False)
        self.select_audio_button.setEnabled(False)
        self.ollama_model_combo.setEnabled(False)
        self.system_prompt_combo.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Get selected values
        system_prompt_path = self.system_prompt_combo.currentData()
        ollama_model = self.ollama_model_combo.currentText()
        
        # Create and start worker
        self.worker = ProcessingWorker(
            self.config_manager,
            self.selected_audio_file,
            system_prompt_path,
            ollama_model
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.update_log)
        self.worker.finished.connect(self.generation_finished)
        self.worker.start()
    
    def update_progress(self, value: int) -> None:
        """Update the progress bar."""
        self.progress_bar.setValue(value)
    
    def update_log(self, message: str) -> None:
        """Update the log text area."""
        self.log_text_edit.append(message)
    
    def generation_finished(self, result: Optional[dict]) -> None:
        """Handle completion of the generation process."""
        self.progress_bar.setValue(100)
        
        # Re-enable UI
        self.make_notes_button.setEnabled(True)
        self.select_audio_button.setEnabled(True)
        self.ollama_model_combo.setEnabled(True)
        self.system_prompt_combo.setEnabled(True)
        
        if result:
            self.save_files(result["notes"], result["transcript"])
        else:
            QMessageBox.critical(
                self,
                "Processing Failed",
                "The note generation process failed. Check the log for details."
            )
    
    def save_files(self, notes: str, transcript: str) -> None:
        """Save the generated notes and transcript to files."""
        base_name = Path(self.selected_audio_file).stem
        timestamped_base_name = get_timestamped_filename(base_name, "")
        # Remove the trailing dot from timestamped filename
        timestamped_base_name = timestamped_base_name[:-1] if timestamped_base_name.endswith('.') else timestamped_base_name
        
        # Save transcript
        txt_file_name, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Transcript", 
            f"{timestamped_base_name}_transcript.txt", 
            "Text Files (*.txt)"
        )
        
        if txt_file_name:
            try:
                with open(txt_file_name, "w", encoding="utf-8") as f:
                    f.write(transcript)
                self.log_text_edit.append(f"Transcript saved to {txt_file_name}")
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Save Error",
                    f"Failed to save transcript: {e}"
                )
        
        # Save notes as PDF
        pdf_file_name, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Notes", 
            f"{timestamped_base_name}_notes.pdf", 
            "PDF Files (*.pdf)"
        )
        
        if pdf_file_name:
            try:
                from reportlab.platypus import SimpleDocTemplate, Paragraph
                from reportlab.lib.styles import getSampleStyleSheet
                
                doc = SimpleDocTemplate(pdf_file_name)
                styles = getSampleStyleSheet()
                
                # Split notes into paragraphs for PDF
                story = []
                for line in notes.split('\n'):
                    if line.strip():  # Skip empty lines
                        story.append(Paragraph(line.replace('\n', '<br/>'), styles['Normal']))
                
                doc.build(story)
                self.log_text_edit.append(f"Notes saved to {pdf_file_name}")
            except ImportError:
                QMessageBox.warning(
                    self,
                    "PDF Library Missing",
                    "reportlab library not found. Cannot save PDF. Install with 'pip install reportlab'"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Save Error",
                    f"Failed to save PDF: {e}"
                )
        
        # Show success message
        QMessageBox.information(
            self,
            "Success",
            "Meeting notes and transcript have been generated successfully!"
        )