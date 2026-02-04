"""
Audio transcription module using Whisper.cpp.
Handles the conversion of audio files to text transcripts.
"""

import subprocess
import os
from typing import Optional
from pathlib import Path


class TranscriptionError(Exception):
    """Custom exception for transcription-related errors."""
    pass


class AudioTranscriber:
    """Manages audio transcription using Whisper.cpp."""
    
    def __init__(self, main_exe_path: str, model_path: str):
        """
        Initialize the transcriber with paths to Whisper.cpp executable and model.

        Args:
            main_exe_path: Path to the Whisper.cpp Whisper.exe executable
            model_path: Path to the Whisper model file (.bin)

        Raises:
            FileNotFoundError: If the executable or model file doesn't exist
        """
        if not os.path.exists(main_exe_path):
            raise FileNotFoundError(f"Whisper.exe not found at {main_exe_path}")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
        
        self.main_exe_path = main_exe_path
        self.model_path = model_path
    
    def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribe an audio file to text using Whisper.cpp.
        
        Args:
            audio_file_path: Path to the audio file to transcribe
            
        Returns:
            The transcribed text
            
        Raises:
            FileNotFoundError: If the audio file doesn't exist
            TranscriptionError: If transcription fails
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found at {audio_file_path}")
        
        # Generate output file path
        audio_path = Path(audio_file_path)
        output_txt_file = audio_path.with_suffix('.txt')
        
        command = [
            self.main_exe_path,
            "-m", self.model_path,
            "-f", audio_file_path,
            "-otxt",  # Output to a text file
        ]
        
        try:
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise TranscriptionError(f"Error during transcription: {stderr}")
            
            if not output_txt_file.exists():
                raise TranscriptionError(f"Transcription output file not found: {output_txt_file}")
            
            # Read the transcript
            with open(output_txt_file, "r", encoding="utf-8") as f:
                transcript = f.read()
            
            # Clean up the temporary text file
            output_txt_file.unlink()
            
            return transcript
            
        except subprocess.SubprocessError as e:
            raise TranscriptionError(f"Subprocess error during transcription: {e}")
        except IOError as e:
            raise TranscriptionError(f"I/O error during transcription: {e}")
        except Exception as e:
            raise TranscriptionError(f"Unexpected error during transcription: {e}")


if __name__ == '__main__':
    # This is for testing purposes.
    # You would need to have Whisper.exe, Whisper.dll, and a model file in the input directory.
    # And an audio file to test with.
    try:
        transcriber = AudioTranscriber(
            main_exe_path="input/Whisper.exe",
            model_path="input/ggml-base.en.bin"  # Assuming a model file is present
        )
        transcript = transcriber.transcribe("input/test_audio.wav")  # Assuming a test audio file
        print(transcript)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except TranscriptionError as e:
        print(f"Transcription error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")