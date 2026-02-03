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
from PyQt5.QtCore import QThread, Qt

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
        # Set application stylesheet for consistent styling
        self.setStyleSheet("""
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
                padding: 15px;
                font-weight: bold;
                font-size: 64pt;
                min-height: 90px;
                font-family: 'Times New Roman', serif;
            }
            QPushButton#generateButton:hover {
                background-color: #b3f2e5;
            }
            QPushButton#generateButton:pressed {
                background-color: #b3f2e5;
            }
            QPushButton:hover {
                background-color: #b3f2e5;
            }
            QPushButton:pressed {
                background-color: #b3f2e5;
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
            QComboBox:focus {
                border: 2px solid #5fa897;
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
        """)

        # Central widget and main layout
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #dcf2ee; font-family: 'Times New Roman', serif; font-size: 12pt;")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        # Title label
        title_label = QLabel("Local Meeting Notes Generator")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-family: 'Times New Roman', serif;
            font-size: 26px;
            font-weight: bold;
            color: #004d4d;
            padding: 15px;
            background-color: #9de3d3;
            border-radius: 10px;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(title_label)

        # Status group
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Status: Initializing...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-family: 'Times New Roman', serif; font-weight: bold; font-size: 13pt;")
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()

        # Audio file selection
        audio_layout = QHBoxLayout()
        self.audio_file_label = QLabel("No file selected")
        self.audio_file_label.setWordWrap(True)
        self.audio_file_label.setStyleSheet("font-family: 'Times New Roman', serif; font-weight: bold; font-size: 12pt;")
        self.select_audio_button = QPushButton("Select Audio File")
        self.select_audio_button.clicked.connect(self.select_audio_file)
        audio_layout.addWidget(self.audio_file_label)  # File detail on the left
        audio_layout.addWidget(self.select_audio_button)  # Button on the right
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

        # Model selection (for .bin files)
        model_bin_layout = QHBoxLayout()
        model_bin_layout.addWidget(QLabel("Transcription Model:"))
        self.model_bin_combo = QComboBox()
        model_bin_layout.addWidget(self.model_bin_combo)
        controls_layout.addLayout(model_bin_layout)

        # Process button
        self.make_notes_button = QPushButton("Generate Meeting Notes")
        self.make_notes_button.setObjectName("generateButton")  # Apply special styling
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

        # Log section (reduced height)
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setMaximumHeight(150)  # Reduced height
        log_layout.addWidget(self.log_text_edit)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
    
    def check_dependencies(self) -> None:
        """Check for required dependencies and update UI accordingly."""
        self.log_text_edit.append("Checking dependencies...")
        config_errors = self.config_manager.validate()
        
        try:
            ollama_models = self.note_generator.get_available_models()
            if not ollama_models:
                config_errors.append("ERROR: No Ollama models found. Please download and set up models using Ollama (e.g., run 'ollama pull llama2' in terminal). Visit https://ollama.ai to download and install Ollama.")
        except NoteGenerationError as e:
            ollama_models = []
            # The error message is already detailed in the NoteGenerator
            config_errors.append(str(e))
        
        if config_errors:
            self.status_label.setText("Status: Error - Missing Dependencies")
            for error in config_errors:
                self.log_text_edit.append(f"{error}")
            self.make_notes_button.setEnabled(False)

            # Show error dialog with detailed information
            error_msg = "\n".join(config_errors)
            QMessageBox.critical(
                self,
                "Dependency Error",
                f"The application is missing required dependencies:\n\n{error_msg}\n\n"
                "Please follow the instructions above to download and set up the required components.\n\n"
                "Visit https://ollama.ai to download and install Ollama, and keep it running when using this application.\n\n"
                "Read the README.md file in the project directory for more information."
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

            # Populate .bin model combo
            self.model_bin_combo.clear()
            model_files = self.config_manager.get_all_model_files(self.config_manager.app_config.input_dir)
            for model_file in model_files:
                self.model_bin_combo.addItem(
                    os.path.basename(model_file),
                    model_file
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
        selected_model_path = self.model_bin_combo.currentData()
        
        # Create and start worker
        self.worker = ProcessingWorker(
            self.config_manager,
            self.selected_audio_file,
            system_prompt_path,
            ollama_model,
            selected_model_path
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
        """Save the generated notes and transcript to three different files in the output folder."""
        base_name = Path(self.selected_audio_file).stem
        timestamped_base_name = get_timestamped_filename(base_name, "")
        # Remove the trailing dot from timestamped filename
        timestamped_base_name = timestamped_base_name[:-1] if timestamped_base_name.endswith('.') else timestamped_base_name

        # Define output file paths in the output directory
        output_dir = Path("output")
        txt_file_path = output_dir / f"{timestamped_base_name}_transcript.txt"
        md_file_path = output_dir / f"{timestamped_base_name}_notes.md"
        pdf_file_path = output_dir / f"{timestamped_base_name}_notes.pdf"

        # Save transcript
        try:
            with open(txt_file_path, "w", encoding="utf-8") as f:
                f.write(transcript)
            self.log_text_edit.append(f"Transcript saved to {txt_file_path}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save transcript: {e}"
            )
            return

        # Save notes as markdown
        try:
            with open(md_file_path, "w", encoding="utf-8") as f:
                f.write(notes)
            self.log_text_edit.append(f"Markdown notes saved to {md_file_path}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save markdown notes: {e}"
            )
            return

        # Save notes as PDF
        try:
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            import re

            doc = SimpleDocTemplate(str(pdf_file_path), pagesize=letter,
                                    rightMargin=72, leftMargin=72,
                                    topMargin=72, bottomMargin=18)
            styles = getSampleStyleSheet()

            # Create custom styles for better formatting
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=24,
                spaceAfter=30,
                alignment=1,  # Center alignment
                textColor=colors.darkblue,
                borderWidth=0,
                borderPadding=0,
                spaceBefore=30
            )

            heading1_style = ParagraphStyle(
                'CustomHeading1',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=14,
                spaceBefore=24,
                textColor=colors.darkgreen,
                borderWidth=0,
                borderPadding=0,
                leftIndent=0
            )

            heading2_style = ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=15,
                spaceAfter=12,
                spaceBefore=18,
                textColor=colors.darkred,
                borderWidth=0,
                borderPadding=0,
                leftIndent=0
            )

            heading3_style = ParagraphStyle(
                'CustomHeading3',
                parent=styles['Heading3'],
                fontSize=13,
                spaceAfter=10,
                spaceBefore=14,
                textColor=colors.darkblue,
                borderWidth=0,
                borderPadding=0,
                leftIndent=0
            )

            # Style for bullet points
            bullet_style = ParagraphStyle(
                'BulletPoints',
                parent=styles['Normal'],
                leftIndent=30,
                spaceAfter=6,
                bulletIndent=15,
                bulletFontName='Helvetica-Bold',
                bulletFontSize=10
            )

            # Split notes into paragraphs for PDF with better markdown parsing
            story = []

            # Add title
            story.append(Paragraph("Meeting Notes", title_style))
            story.append(Spacer(1, 0.25 * inch))

            # Process the notes content with better markdown parsing
            lines = notes.split('\n')
            i = 0

            while i < len(lines):
                line = lines[i].strip()

                if not line:
                    story.append(Spacer(1, 0.15 * inch))
                    i += 1
                    continue

                # Check if line looks like a markdown header
                if line.startswith('#'):
                    # Handle markdown headers
                    level = len(line) - len(line.lstrip('#'))
                    header_text = line.lstrip('# ').strip()

                    if level == 1:
                        story.append(Paragraph(header_text, heading1_style))
                    elif level == 2:
                        story.append(Paragraph(header_text, heading2_style))
                    elif level >= 3:
                        story.append(Paragraph(header_text, heading3_style))

                # Check for thematic breaks (horizontal rules)
                elif line.startswith('---') or line.startswith('***') or line.startswith('___'):
                    story.append(Spacer(1, 0.2 * inch))
                    # Add a horizontal line
                    d = SimpleDocTemplate
                    from reportlab.graphics.shapes import Line, Drawing
                    line_shape = Line(0, 0, 6.5*inch, 0)
                    line_shape.strokeColor = colors.grey
                    line_shape.strokeWidth = 1
                    drawing = Drawing(6.5*inch, 1)
                    drawing.add(line_shape)
                    story.append(drawing)
                    story.append(Spacer(1, 0.2 * inch))

                # Check for bullet points or lists
                elif line.startswith(('- ', '* ', '+ ')) or re.match(r'^\d+\.', line):
                    # Handle lists - collect all list items
                    list_items = []
                    while i < len(lines) and (lines[i].strip().startswith(('- ', '* ', '+ ')) or
                                              re.match(r'^\d+\.', lines[i].strip()) or
                                              (len(list_items) > 0 and
                                               lines[i].strip().startswith('  ') and
                                               not lines[i].strip().startswith('#'))):  # Continuation of list item
                        list_line = lines[i].strip()
                        if list_line:
                            # Format the list item properly
                            if list_line.startswith(('- ', '* ', '+ ')):
                                # Replace with proper bullet character
                                list_item = "&bull; " + list_line[2:]
                            elif re.match(r'^\d+\.', list_line):
                                # Numbered list
                                list_item = list_line
                            else:
                                # Indented continuation of list item
                                list_item = "&nbsp;&nbsp;&nbsp;" + list_line.strip()

                            list_items.append(Paragraph(list_item, bullet_style))
                        i += 1

                    # Add all list items to the story
                    for item in list_items:
                        story.append(item)
                    story.append(Spacer(1, 0.1 * inch))
                    continue  # Skip incrementing i since we already did it in the loop

                # Check for bold, italic, strikethrough, and code formatting
                elif ('**' in line or '*' in line or '~~' in line or '`' in line):
                    # Process markdown formatting
                    formatted_line = line
                    # Replace **text** with bold
                    formatted_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_line)
                    # Replace *text* or _text_ with italic
                    formatted_line = re.sub(r'\*(.*?)\*|_(.*?)_', r'<i>\1\2</i>', formatted_line)
                    # Replace ~~text~~ with strikethrough
                    formatted_line = re.sub(r'~~(.*?)~~', r'<strike>\1</strike>', formatted_line)
                    # Replace `code` with monospace
                    formatted_line = re.sub(r'`(.*?)`', r'<font face="Courier">\\1</font>', formatted_line)
                    # Replace ```code block``` with monospace and background
                    formatted_line = re.sub(r'```(.*?)```', r'<font face="Courier">\\1</font>', formatted_line)

                    story.append(Paragraph(formatted_line, styles['Normal']))

                # Check for links
                elif '](' in line:
                    # Process markdown links [text](url)
                    formatted_line = re.sub(r'\[(.*?)\]\((.*?)\)', r'<link href="\2">\1</link>', line)
                    story.append(Paragraph(formatted_line, styles['Normal']))

                # Check for inline images
                elif '![' in line and ']' in line and '(' in line and ')' in line:
                    # Extract image markdown: ![alt text](image_url)
                    img_match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
                    if img_match:
                        alt_text, img_url = img_match.groups()
                        # If it's a local icon file, try to embed it
                        try:
                            if img_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                                img = Image(img_url)
                                img.drawHeight = 0.5 * inch
                                img.drawWidth = 0.5 * inch
                                story.append(img)
                                # Add alt text as caption
                                if alt_text:
                                    story.append(Paragraph(alt_text, styles['Italic']))
                        except:
                            # If image can't be loaded, just add alt text
                            if alt_text:
                                story.append(Paragraph(alt_text, styles['Italic']))
                    else:
                        story.append(Paragraph(line, styles['Normal']))

                # Regular paragraph
                else:
                    story.append(Paragraph(line, styles['Normal']))

                story.append(Spacer(1, 0.1 * inch))
                i += 1

            doc.build(story)
            self.log_text_edit.append(f"PDF notes saved to {pdf_file_path}")
        except ImportError:
            QMessageBox.warning(
                self,
                "PDF Library Missing",
                "reportlab library not found. Cannot save PDF. Install with 'pip install reportlab'"
            )
            return
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save PDF: {e}"
            )
            return

        # Show success message
        QMessageBox.information(
            self,
            "Success",
            f"Meeting notes and transcript have been generated successfully!\n\n"
            f"Files saved to:\n"
            f"- {txt_file_path} (Transcript)\n"
            f"- {md_file_path} (Markdown Notes)\n"
            f"- {pdf_file_path} (PDF Notes)"
        )