# Meeting Notes Maker - Agent Documentation

## Overview
Meeting Notes Maker is a professional-grade Windows desktop application that processes meeting audio files locally and generates formatted meeting notes. The application works entirely offline (except for initial setup) and handles all processing on the user's machine with a clean, maintainable architecture.

## Purpose
The application is designed to transform audio recordings of meetings into structured, professional meeting notes using AI technology. It leverages local AI models for privacy and performance, eliminating the need for cloud processing of sensitive meeting content.

## Architecture
The application follows a clean architecture pattern with four distinct layers:

### 1. Presentation Layer
- **Location**: `Presentation/`
- **Technologies**: WPF, MVVM pattern
- **Components**: ViewModels, Views, Converters
- **Responsibilities**: User interface, user interactions, data binding
- **Key Files**:
  - `Presentation/ViewModels/MainViewModel.cs` - Main application logic
  - `MainWindow.xaml` - Primary user interface
  - `MainWindow.xaml.cs` - Window initialization and DI setup

### 2. Application Layer
- **Location**: `Application/`
- **Technologies**: C#, DTOs, Commands
- **Components**: Services interfaces, DTOs, Commands, Common utilities
- **Responsibilities**: Orchestration of business use cases, data transfer objects
- **Key Files**:
  - `Application/Services/IMeetingProcessingService.cs` - Core processing orchestration
  - `Application/DTOs/` - Data transfer objects for clean layer boundaries

### 3. Domain Layer
- **Location**: `Domain/`
- **Technologies**: C#, Domain-driven design
- **Components**: Entities, Services, Repositories, Common utilities
- **Responsibilities**: Business logic, domain entities, business rules
- **Key Files**:
  - `Domain/Entities/MeetingNote.cs` - Core meeting note entity
  - `Domain/Services/` - Domain service interfaces

### 4. Infrastructure Layer
- **Location**: `Infrastructure/`
- **Technologies**: C#, External integrations
- **Components**: External services, Configuration, Logging, File system
- **Responsibilities**: External integrations, file operations, configuration
- **Key Files**:
  - `Infrastructure/Services/WhisperService.cs` - Audio transcription
  - `Infrastructure/Services/OllamaService.cs` - AI processing
  - `Infrastructure/Services/PdfGenerationService.cs` - PDF creation

## Key Features

### Audio Processing
- Supports MP3, WAV, FLAC, and M4A audio formats
- Local processing using Whisper models for speech-to-text conversion
- Progress reporting during transcription

### AI Integration
- Integration with local Ollama models for intelligent note generation
- Configurable system prompts for tailored note generation
- Automatic extraction of key discussion points, decisions, action items, deadlines, and Q&A

### Output Generation
- Professional PDF meeting notes with structured formatting
- Raw transcript in TXT format
- Organized file management with timestamped outputs

### User Interface
- Clean WPF interface with intuitive workflow
- Real-time progress reporting
- Comprehensive error handling and validation
- Responsive UI with asynchronous operations

## Dependencies

### NuGet Packages
- `OllamaSharp` - Ollama API client for AI model integration
- `QuestPDF` - PDF generation library
- `Whisper.net` - Whisper model integration
- `NAudio` - Audio file handling
- `Microsoft.Extensions.DependencyInjection` - Dependency injection
- `Microsoft.Extensions.Configuration.Json` - Configuration management
- `Serilog` - Structured logging
- `FluentValidation` - Input validation
- `CommunityToolkit.Mvvm` - MVVM toolkit

### External Requirements
- Ollama (for AI models) - https://ollama.ai/
- Whisper models (.bin files) - https://github.com/ggerganov/whisper.cpp
- Local installation of required AI models

## Configuration
The application uses `appsettings.json` for configuration:

```json
{
  "AppSettings": {
    "OllamaApiUrl": "http://localhost:11434",
    "OllamaDefaultModel": "llama2",
    "DefaultWorkingDirectory": "",
    "MaxFileSizeMB": 100,
    "TranscriptionTimeoutSeconds": 300,
    "WhisperModelPath": "./Models/",
    "WhisperDefaultLanguage": "en"
  }
}
```

## File Structure
```
MeetingNotesMaker/
├── Application/          # Application layer (use cases, DTOs)
│   ├── Commands/
│   ├── Common/
│   ├── DTOs/
│   └── Services/
├── Domain/              # Domain layer (entities, business rules)
│   ├── Common/
│   ├── Entities/
│   ├── Repositories/
│   └── Services/
├── Infrastructure/      # Infrastructure layer (external integrations)
│   ├── Configuration/
│   ├── Exceptions/
│   ├── FileSystem/
│   ├── Logging/
│   └── Services/
├── Presentation/        # Presentation layer (UI, ViewModels)
│   ├── Common/
│   ├── Converters/
│   ├── ViewModels/
│   └── Views/
├── Tests/               # Unit and integration tests
│   ├── Unit/
│   └── Functional/
├── TranscribingBins/    # Whisper model binaries
├── MeetingTranscriptions/ # Generated transcripts
├── MeetingNotes/        # Generated PDF notes
├── logs/                # Application logs
├── bin/                 # Build output (can be deleted)
├── obj/                 # Build intermediates (can be deleted)
├── App.config           # Legacy config (being migrated)
├── appsettings.json     # Modern configuration
├── MainWindow.xaml      # Main UI
├── MainWindow.xaml.cs   # UI code-behind
├── MeetingNotesMaker.csproj # Project file
├── README.md            # User documentation
├── PROJECT_SUMMARY.md   # Project summary
├── REFCTORING_SUMMARY.md # Refactoring documentation
└── To_Do.md             # Development tasks
```

## Core Workflow
1. User selects an audio file using the "Select Audio File" button
2. User selects a Whisper model file for transcription
3. User selects a system prompt file for note generation
4. User selects an Ollama model from the dropdown
5. User clicks "Process Meeting" to start transcription and note generation
6. Application transcribes audio using Whisper
7. Application sends transcript to Ollama with system prompt
8. Application structures the AI response into meeting notes
9. Application generates PDF and TXT outputs
10. User can save the generated PDF and TXT files

## Security Considerations
- Input validation and sanitization
- Path traversal protection
- Secure file handling
- Local processing for privacy

## Error Handling
- Structured exception hierarchy
- Domain, application, and infrastructure exceptions
- Comprehensive logging with Serilog
- User-friendly error messages

## Testing Strategy
- Unit tests for business logic
- Integration tests for service layers
- Mockable dependencies through DI
- Clear contracts between layers

## Build Instructions
1. Ensure .NET 8.0 SDK is installed
2. Install required NuGet packages: `dotnet restore`
3. Build the solution: `dotnet build`
4. Run the application: `dotnet run`

## Deployment
The application is distributed as a Windows executable that includes all necessary dependencies. Users need to separately install Ollama and download Whisper models.

## Maintenance Notes
- The application follows SOLID principles
- Dependency injection throughout
- Separation of concerns with clean architecture
- Comprehensive logging for troubleshooting
- Extensive error handling and validation

## 🚨 PROJECT STATUS: SUSPENDED 🚨

### Current Issues (Causing Suspension)
1. **Whisper Executable Integration Problems**:
   - The Whisper transcription service encounters errors during audio processing
   - Exit code -2147024894 indicates issues with the underlying Whisper executable
   - Despite successful transcription output being generated, the process fails during SRT file handling
   - Media Foundation decoding errors occur when processing certain audio formats

2. **External Dependency Failures**:
   - The Whisper executable (main.exe) has compatibility issues with certain audio codecs
   - Temporary file handling in the transcription process causes failures
   - GPU acceleration conflicts with certain graphics drivers

3. **Incomplete Output Pipeline**:
   - While the transcript is generated successfully, the process fails before saving files to the Output folder
   - The meeting notes generation stage is not reached due to transcription failures

### Implemented Features (Working Components)
✅ UI has been updated to remove unnecessary "Save PDF" and "Save Transcript" buttons
✅ Output folder creation and management is implemented in MeetingProcessingService
✅ Transcript saving and loading from the Output folder is coded
✅ Meeting notes generation pipeline is structured correctly
✅ The application builds successfully without compilation errors

### Planned Improvements (For Resumption)
1. **Alternative Transcription Engine**:
   - Integrate Whisper.net library instead of relying on external executable
   - Implement fallback transcription methods for better reliability
   - Add support for additional audio format conversions

2. **Enhanced Error Handling**:
   - Implement graceful degradation when transcription fails
   - Add detailed logging for debugging transcription issues
   - Create recovery mechanisms for partial failures

3. **Improved File Management**:
   - Ensure Output folder is created regardless of transcription success
   - Implement atomic file operations to prevent corruption
   - Add file validation and cleanup routines

4. **Better Audio Format Support**:
   - Integrate audio preprocessing to normalize input formats
   - Add automatic format conversion before transcription
   - Implement codec detection and handling

5. **Robust Process Management**:
   - Replace external executable calls with native .NET implementations
   - Add timeout and retry mechanisms for transcription
   - Implement health checks for external dependencies