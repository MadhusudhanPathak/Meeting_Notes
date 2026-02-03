"""
Utility functions for the Local Meeting Notes application.
Contains helper functions for file operations, formatting, etc.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional


def get_timestamped_filename(base_name: str, extension: str) -> str:
    """
    Generate a filename with a timestamp.
    
    Args:
        base_name: Base name for the file
        extension: File extension (without dot)
        
    Returns:
        Filename with timestamp in the format: {base_name}_YYYY-MM-DD_HH-MM-SS.{extension}
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if extension.startswith('.'):
        extension = extension[1:]  # Remove leading dot if present
    return f"{base_name}_{timestamp}.{extension}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.
    
    Args:
        filename: Original filename to sanitize
        
    Returns:
        Sanitized filename safe for the filesystem
    """
    # Replace invalid characters for most filesystems
    invalid_chars = '<>:"/\\|?*'
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Limit length to avoid filesystem issues
    if len(sanitized) > 255:
        name_part = sanitized[:200]  # Leave room for extension
        ext_part = Path(sanitized).suffix
        sanitized = name_part + ext_part
    
    return sanitized


def validate_audio_file(filepath: str) -> bool:
    """
    Validate if a file is an acceptable audio file.
    
    Args:
        filepath: Path to the file to validate
        
    Returns:
        True if the file is a valid audio file, False otherwise
    """
    valid_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg'}
    file_ext = Path(filepath).suffix.lower()
    return file_ext in valid_extensions


def validate_output_directory(directory: str) -> tuple[bool, Optional[str]]:
    """
    Validate if an output directory is valid and writable.
    
    Args:
        directory: Path to the directory to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    dir_path = Path(directory)
    
    if not dir_path.exists():
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Cannot create directory: {e}"
    
    if not dir_path.is_dir():
        return False, "Path is not a directory"
    
    try:
        # Test if we can write to the directory
        test_file = dir_path / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True, None
    except Exception as e:
        return False, f"Directory is not writable: {e}"


if __name__ == "__main__":
    # Test the utility functions
    print("Testing get_timestamped_filename:")
    print(get_timestamped_filename("meeting", "pdf"))
    
    print("\nTesting sanitize_filename:")
    print(sanitize_filename('invalid<file>:name.txt'))
    
    print("\nTesting validate_audio_file:")
    print(validate_audio_file("test.mp3"))
    print(validate_audio_file("test.txt"))
    
    print("\nTesting validate_output_directory:")
    print(validate_output_directory("./test_dir"))