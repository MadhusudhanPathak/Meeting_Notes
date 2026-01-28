# Meeting Notes App - Technical To-Do

## 1. Project Setup
- Create WPF .NET 6/7 project targeting Windows
- Install NuGet packages: `OllamaSharp`, `PdfSharp` or `iTextSharp`, `Newtonsoft.Json`
- Add native Whisper.cpp C# wrapper from https://github.com/Const-me/Whisper

## 2. Core Components to Build

### A. Whisper Integration
- Create `WhisperService.cs` class
- Load `.bin` model file from working directory
- Implement `TranscribeAudio(string filePath, IProgress<int> progress)` method
- Return full transcript as string
- Handle file format validation (MP3/WAV)

### B. Ollama Integration  
- Create `OllamaService.cs` class
- Implement `GetInstalledModels()` to list local Ollama models via API
- Implement `GenerateNotes(string transcript, string systemPrompt, string modelName)` method
- Use Ollama API endpoint (default: http://localhost:11434)

### C. File Management
- Create `FileService.cs` class
- `LoadSystemPrompts()` - scan directory for `*_Prompt.txt` files
- `FindWhisperModel()` - locate `.bin` file in working directory
- `SavePDF(string content, string path)` - generate formatted PDF
- `SaveTranscript(string content, string path)` - save raw TXT

### D. Startup Validation
- Create `DependencyChecker.cs` class
- Check for System_Prompt.txt existence
- Check for .bin Whisper model
- Verify Ollama is running (HTTP ping to localhost:11434)
- Return validation results with specific error messages

## 3. UI Structure (MainWindow.xaml)

### Layout Sections:
1. **Status Bar** (top) - dependency status indicators
2. **Input Section**: 
   - File picker button
   - Ollama model dropdown (bind to available models)
   - System prompt dropdown (bind to found prompt files)
3. **Processing Section**:
   - "Process Meeting" button
   - Progress bar with status label
4. **Output Section**:
   - Save location textbox with browse button
   - Save buttons for PDF/TXT

## 4. MainWindow.xaml.cs Logic

### Key Methods:
```
- OnLoaded(): Run DependencyChecker, populate dropdowns
- SelectAudioFile_Click(): Open file dialog
- ProcessMeeting_Click(): 
  * Call WhisperService.TranscribeAudio()
  * Update progress bar
  * Call OllamaService.GenerateNotes()
  * Enable save buttons
- SavePDF_Click(): Use FileService.SavePDF()
- SaveTranscript_Click(): Use FileService.SaveTranscript()
```

### State Management:
- Store transcript and notes in class-level variables
- Disable/enable buttons based on processing state
- Use async/await for all long operations

## 5. Error Handling Requirements

- Wrap all file I/O in try-catch
- Display MessageBox for critical errors
- Show inline warnings for missing dependencies
- Provide setup instructions in error messages:
  * Link to Whisper model download
  * "Install Ollama from ollama.ai"
  * Show System_Prompt.txt template

## 6. Default Filenames
- PDF: `Meeting_Notes_{DateTime.Now:yyyyMMdd_HHmmss}.pdf`
- TXT: `Transcript_{DateTime.Now:yyyyMMdd_HHmmss}.txt`

## 7. README.md Must Include
- Prerequisites: Ollama installation, Whisper model download link
- Setup: Place `.bin` file and `System_Prompt.txt` in app directory
- Example System_Prompt.txt template
- Troubleshooting common issues