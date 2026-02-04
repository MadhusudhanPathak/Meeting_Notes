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
- `Whisper.dll` - Whisper.cpp dependency
- `.bin` model files (e.g., `ggml-medium.bin`) - Whisper models
- `*.txt` - System prompt templates for note generation (any .txt file in the input folder)

The application also expects the following file in the current directory:
- `Whisper.exe` - Whisper.cpp executable

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
- Modern UI design with Times New Roman font, teal color scheme (#dcf2ee), and intuitive layout
- Larger, more prominent "Generate Meeting Notes" button with 64pt font
- Improved button hover and selection effects
- Rearranged controls with file details on left and action buttons on right

## Technical Details

### GUI Architecture
- Built with PyQt5
- Uses QThread for background processing to prevent UI freezing
- Progress bar and log display for user feedback
- Worker thread handles transcription and note generation sequentially
- Modular UI components with clear separation of concerns
- Modern styling with Times New Roman font, teal color scheme, and rounded corners
- Responsive layout with appropriate sizing for all elements

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
- Presence of `Whisper.exe` in the current directory
- Presence of `Whisper.dll` in the current directory
- At least one `.bin` model file in the `input/` directory
- At least one `*.txt` file in the `input/` directory for system prompts
- Accessibility of local Ollama instance

## File Descriptions

### main.py
Application entry point that creates and shows the main window.

### src/ui/main_window.py
Contains the MainWindow class with:
- UI layout and widgets with modern styling
- File selection functionality
- Processing workflow management
- Background worker thread implementation
- Progress and logging display
- Comprehensive error handling and user feedback
- Modern UI elements with Times New Roman font and teal color scheme

### src/config/settings.py
Contains the ConfigManager class that:
- Manages paths to required executables and models
- Validates dependencies
- Handles system prompt file discovery and loading (now supports all .txt files)
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
- Provides detailed error messages for Ollama issues

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
4. User selects Whisper model for transcription
5. User initiates processing
6. Application transcribes audio using Whisper.cpp
7. Application generates notes using Ollama
8. Application saves transcript (TXT) and notes (PDF) to output directory

## Important Notes
- The application requires Whisper.cpp binaries and models to be placed in the appropriate directories
- Ollama must be installed and running locally for note generation to work
- All processing happens locally on the user's machine
- The application generates both raw transcripts and AI-enhanced meeting notes
- The codebase follows industry-standard architecture with clear separation of concerns
- Proper error handling and input validation have been implemented throughout
- The application has a modern UI with Times New Roman font and teal color scheme
- The "Generate Meeting Notes" button is prominently displayed with large text
- The application now supports all .txt files in the input folder as system prompts
- Improved error messages guide users to download required components from appropriate sources