"""
Background processing worker for the Local Meeting Notes application.
Handles transcription only in a separate thread (without Ollama).
"""

from PyQt5.QtCore import QThread, pyqtSignal
from typing import Dict, Any, Optional

from src.models.transcriber import AudioTranscriber, TranscriptionError
from src.config.settings import ConfigManager
from pathlib import Path


class TranscriptionOnlyWorker(QThread):
    """Worker thread for handling audio transcription only (without note generation)."""

    # Signals for communication with the main thread
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(
        self,
        config_manager: ConfigManager,
        selected_audio_file: str,
        selected_model_path: str
    ):
        """
        Initialize the transcription-only worker.

        Args:
            config_manager: Configuration manager instance
            selected_audio_file: Path to the audio file to process
            selected_model_path: Path to the selected .bin model file
        """
        super().__init__()
        self.config_manager = config_manager
        self.selected_audio_file = selected_audio_file
        self.selected_model_path = selected_model_path

    def run(self) -> None:
        """Execute the transcription process only."""
        try:
            self.log.emit("Starting audio transcription...")

            # Step 1: Transcription
            self.log.emit("Transcribing audio...")
            self.progress.emit(20)

            transcriber = AudioTranscriber(
                self.config_manager.app_config.main_exe_path,
                self.selected_model_path
            )
            transcript = transcriber.transcribe(self.selected_audio_file)
            self.log.emit("Transcription complete.")
            self.progress.emit(90)

            # Emit the result
            result = {
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
        except Exception as e:
            import traceback
            error_msg = f"An unexpected error occurred: {str(e)}\n{traceback.format_exc()}"
            self.log.emit(error_msg)
            self.finished.emit(None)