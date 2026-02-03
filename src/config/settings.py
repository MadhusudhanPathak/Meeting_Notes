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
        # Look for main.exe and Whisper.dll in the current directory
        self.app_config = AppConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            main_exe_path="main.exe",  # Look in current directory
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
        return glob.glob(os.path.join(input_dir, "System_Prompt*.txt"))
    
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
            errors.append(f"main.exe not found in {self.app_config.input_dir}")
        
        if not os.path.exists(self.app_config.whisper_dll_path):
            errors.append(f"Whisper.dll not found in {self.app_config.input_dir}")
        
        if not self.app_config.model_path:
            errors.append(f"No .bin model file found in {self.app_config.input_dir}")
        
        if not self.app_config.system_prompt_paths:
            errors.append(f"No System_Prompt*.txt file found in {self.app_config.input_dir}")
        
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