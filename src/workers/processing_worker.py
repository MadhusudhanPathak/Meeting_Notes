"""
Background processing worker for the Local Meeting Notes application.
Handles transcription and note generation in a separate thread.
"""

from PyQt5.QtCore import QThread, pyqtSignal
from typing import Dict, Any, Optional

from src.models.transcriber import AudioTranscriber, TranscriptionError
from src.core.note_generator import NoteGenerator, NoteGenerationError
from src.config.settings import ConfigManager


class ProcessingWorker(QThread):
    """Worker thread for handling audio transcription and note generation."""
    
    # Signals for communication with the main thread
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(object)
    
    def __init__(
        self,
        config_manager: ConfigManager,
        selected_audio_file: str,
        system_prompt_path: str,
        ollama_model: str,
        selected_model_path: str
    ):
        """
        Initialize the processing worker.

        Args:
            config_manager: Configuration manager instance
            selected_audio_file: Path to the audio file to process
            system_prompt_path: Path to the system prompt file
            ollama_model: Name of the Ollama model to use
            selected_model_path: Path to the selected .bin model file
        """
        super().__init__()
        self.config_manager = config_manager
        self.selected_audio_file = selected_audio_file
        self.system_prompt_path = system_prompt_path
        self.ollama_model = ollama_model
        self.selected_model_path = selected_model_path
    
    def run(self) -> None:
        """Execute the transcription and note generation process."""
        try:
            self.log.emit("Starting meeting notes generation...")
            
            # Step 1: Transcription
            self.log.emit("Transcribing audio...")
            self.progress.emit(10)
            
            transcriber = AudioTranscriber(
                self.config_manager.app_config.main_exe_path,
                self.selected_model_path
            )
            transcript = transcriber.transcribe(self.selected_audio_file)
            self.log.emit("Transcription complete.")
            self.progress.emit(50)
            
            # Step 2: Note Generation
            self.log.emit("Generating notes...")
            system_prompt = self.config_manager.get_system_prompt(self.system_prompt_path)
            
            if system_prompt is None:
                raise ValueError(f"Could not load system prompt from {self.system_prompt_path}")
            
            note_generator = NoteGenerator()
            notes = note_generator.generate_notes(transcript, system_prompt, self.ollama_model)
            self.log.emit("Note generation complete.")
            self.progress.emit(90)
            
            # Emit the result
            result = {
                "notes": notes,
                "transcript": transcript
            }
            self.finished.emit(result)
            
        except FileNotFoundError as e:
            error_msg = f"File not found: {str(e)}"
            self.log.emit(error_msg)
            self.finished.emit(None)
        except TranscriptionError as e:
            error_msg = f"Transcription error: {str(e)}"
            self.log.emit(error_msg)
            self.finished.emit(None)
        except NoteGenerationError as e:
            error_msg = f"Note generation error: {str(e)}"
            self.log.emit(error_msg)
            self.finished.emit(None)
        except ValueError as e:
            error_msg = f"Value error: {str(e)}"
            self.log.emit(error_msg)
            self.finished.emit(None)
        except Exception as e:
            import traceback
            error_msg = f"An unexpected error occurred: {str(e)}\n{traceback.format_exc()}"
            self.log.emit(error_msg)
            self.finished.emit(None)