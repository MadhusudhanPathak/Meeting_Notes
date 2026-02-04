"""
Configuration management module for the Local Meeting Notes application.
Handles application settings, paths, and validation.
"""

import os
import glob
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class AppConfig:
    """Application configuration data class."""
    
    input_dir: str = "input"
    output_dir: str = "output"
    main_exe_path: str = ""
    whisper_dll_path: str = ""
    model_path: str = ""
    system_prompt_paths: List[str] = None
    
    def __post_init__(self):
        if self.system_prompt_paths is None:
            self.system_prompt_paths = []


class ConfigManager:
    """Manages application configuration and validation."""
    
    def __init__(self, input_dir: str = "input", output_dir: str = "output"):
        # Look for Whisper.exe and Whisper.dll in the current directory
        self.app_config = AppConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            main_exe_path="Whisper.exe",  # Look in current directory
            whisper_dll_path="Whisper.dll",  # Look in current directory
            model_path=self._find_model_file(input_dir),
            system_prompt_paths=self._find_system_prompt_files(input_dir)
        )
    
    @staticmethod
    def _find_model_file(input_dir: str) -> Optional[str]:
        """Find the first .bin model file in the input directory."""
        models = glob.glob(os.path.join(input_dir, "*.bin"))
        return models[0] if models else None

    @staticmethod
    def get_all_model_files(input_dir: str) -> List[str]:
        """Get all .bin model files in the input directory."""
        return glob.glob(os.path.join(input_dir, "*.bin"))
    
    @staticmethod
    def _find_system_prompt_files(input_dir: str) -> List[str]:
        """Find all system prompt files in the input directory."""
        return glob.glob(os.path.join(input_dir, "*.txt"))
    
    def get_system_prompt(self, file_path: str) -> Optional[str]:
        """Read and return the content of a system prompt file."""
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except (IOError, OSError) as e:
            print(f"Error reading system prompt file {file_path}: {e}")
            return None
    
    def validate(self) -> List[str]:
        """Validate all required dependencies and return a list of errors."""
        errors = []

        if not os.path.exists(self.app_config.main_exe_path):
            errors.append(f"ERROR: Whisper.exe not found in current directory. Please download Whisper.cpp binaries from https://github.com/Const-me/Whisper and place Whisper.exe in the same directory as main.py")

        if not os.path.exists(self.app_config.whisper_dll_path):
            errors.append(f"ERROR: Whisper.dll not found in current directory. Please download Whisper.cpp binaries from https://github.com/Const-me/Whisper and place Whisper.dll in the same directory as main.py")

        if not self.app_config.model_path:
            errors.append(f"ERROR: No .bin model file found in {self.app_config.input_dir}. Please download a model file from https://huggingface.co/ggerganov/whisper.cpp/tree/main and place it in the input folder. You can have multiple .bin files in the input folder and select from the dropdown.")

        if not self.app_config.system_prompt_paths:
            errors.append(f"ERROR: No System_Prompt*.txt file found in {self.app_config.input_dir}. Please create a text file with your base system prompt for meeting notes generation in the input folder. You can have multiple system prompt files in the input folder and select from the dropdown.")

        # Add general guidance message
        if errors:
            errors.append("")
            errors.append("INFO: For more information, please read the README.md file in the project directory.")
            errors.append("INFO: You can download .bin model files from https://huggingface.co/ggerganov/whisper.cpp/tree/main")
            errors.append("INFO: Create a text file with your system prompt in the input folder (e.g., System_Prompt_Meeting_Notes.txt)")

        return errors


if __name__ == '__main__':
    config = ConfigManager()
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"- {error}")
    else:
        print("Configuration is valid.")
        cfg = config.app_config
        print(f"Main exe: {cfg.main_exe_path}")
        print(f"Whisper.dll: {cfg.whisper_dll_path}")
        print(f"Model: {cfg.model_path}")
        print(f"System Prompts: {cfg.system_prompt_paths}")
        if cfg.system_prompt_paths:
            print("\nFirst System Prompt content:")
            print(config.get_system_prompt(cfg.system_prompt_paths[0]))