# Local Meeting Notes Application - Codebase Overview

## Project Summary
This is a Windows desktop application that processes meeting audio files locally and generates formatted meeting notes. The application works entirely offline (except for initial setup) and handles all processing on the user's machine using Python, Whisper.cpp for transcription, and Ollama for AI-powered note generation.

## Architecture
The application follows a modern, modular architecture with the following key components:

### Main Components
1. **main.py** - Entry point of the application, initializes the Qt GUI
2. **src/ui/main_window.py** - Contains the main GUI window and UI logic
3. **src/config/settings.py** - Handles configuration, dependency validation, and system prompt management
4. **src/models/transcriber.py** - Manages audio transcription using Whisper.cpp
5. **src/core/note_generator.py** - Interfaces with Ollama API to generate structured meeting notes
6. **src/utils/helpers.py** - Utility functions for file naming and validation
7. **src/workers/processing_worker.py** - Background processing thread for transcription and note generation

### Input Directory Structure
The application expects the following files in the `input` directory:
- `main.exe` - Whisper.cpp executable
- `Whisper.dll` - Whisper.cpp dependency
- `.bin` model files (e.g., `ggml-medium.bin`) - Whisper models
- `System_Prompt*.txt` - System prompt templates for note generation

## Key Features
- Audio file selection (MP3/WAV/M4A/FLAC/AAC/OGG support)
- Local audio transcription using Whisper.cpp
- AI-powered meeting note generation using Ollama
- PDF and TXT output generation
- Progress tracking and logging
- Model and system prompt selection via dropdowns
- Dependency validation on startup
- Comprehensive error handling and input validation
- Professional UI with responsive design

## Technical Details

### GUI Architecture
- Built with PyQt5
- Uses QThread for background processing to prevent UI freezing
- Progress bar and log display for user feedback
- Worker thread handles transcription and note generation sequentially
- Modular UI components with clear separation of concerns

### Processing Pipeline
1. Audio transcription using Whisper.cpp (local processing)
2. Note generation using Ollama API (requires local Ollama instance)
3. Output formatting and file saving

### Dependencies
- Whisper.cpp (for transcription)
- Ollama (for AI processing)
- PyQt5 (for GUI)
- reportlab (for PDF generation)
- requests (for Ollama API communication)
- urllib3 (for retry strategies)

### Configuration Validation
The application validates the following on startup:
- Presence of `main.exe` in the input directory
- Presence of `Whisper.dll` in the input directory
- At least one `.bin` model file in the input directory
- At least one `System_Prompt*.txt` file in the input directory
- Accessibility of local Ollama instance

## File Descriptions

### main.py
Application entry point that creates and shows the main window.

### src/ui/main_window.py
Contains the MainWindow class with:
- UI layout and widgets
- File selection functionality
- Processing workflow management
- Background worker thread implementation
- Progress and logging display
- Comprehensive error handling and user feedback

### src/config/settings.py
Contains the ConfigManager class that:
- Manages paths to required executables and models
- Validates dependencies
- Handles system prompt file discovery and loading
- Implements configuration validation with detailed error reporting

### src/models/transcriber.py
Contains the AudioTranscriber class that:
- Executes Whisper.cpp for audio transcription
- Manages transcription process and output
- Handles error cases during transcription
- Implements proper resource cleanup

### src/core/note_generator.py
Contains the NoteGenerator class that:
- Communicates with Ollama API
- Generates structured meeting notes from transcripts
- Manages available model discovery
- Implements retry strategies and timeout handling

### src/utils/helpers.py
Contains utility functions for:
- Timestamped filename generation
- File validation and sanitization
- Input validation utilities

### src/workers/processing_worker.py
Contains the ProcessingWorker class that:
- Handles background processing in a separate thread
- Manages transcription and note generation workflow
- Provides progress updates to the UI
- Implements proper error handling for background tasks

## Usage Flow
1. Application starts and validates dependencies
2. User selects an audio file
3. User chooses Ollama model and system prompt
4. User initiates processing
5. Application transcribes audio using Whisper.cpp
6. Application generates notes using Ollama
7. User saves transcript (TXT) and notes (PDF) to desired locations

## Important Notes
- The application requires Whisper.cpp binaries and models to be placed in the input directory
- Ollama must be running locally for note generation to work
- All processing happens locally on the user's machine
- The application generates both raw transcripts and AI-enhanced meeting notes
- The codebase now follows industry-standard architecture with clear separation of concerns
- Proper error handling and input validation have been implemented throughout
- The application is now more maintainable and scalable for future enhancements