using System.Windows.Input;
using MeetingNotesMaker.Application.DTOs;
using MeetingNotesMaker.Application.Services;
using MeetingNotesMaker.Presentation.Common;
using Microsoft.Win32;
using System.Collections.ObjectModel;
using MeetingNotesMaker.Infrastructure.Services;
using MeetingNotesMaker.Domain.Services;
using System.IO;

namespace MeetingNotesMaker.Presentation.ViewModels
{
    public class MainViewModel : BaseViewModel
    {
        private readonly IMeetingProcessingService _meetingProcessingService;
        private readonly IFileValidationService _fileValidationService;
        private readonly IFileService _fileService;
        private readonly IMeetingNoteGenerationService _noteGenerationService;

        private string _selectedAudioFile = string.Empty;
        private string _selectedModel = string.Empty;
        private string _selectedWhisperModelPath = string.Empty;
        private string _selectedSystemPromptPath = string.Empty;
        private string _progressText = string.Empty;
        private int _progressValue;
        private bool _isProcessing;
        private string _statusMessage = string.Empty;
        private string _transcriptPreview = string.Empty;
        private ObservableCollection<string> _availableModels = new ObservableCollection<string>();

        public MainViewModel(
            IMeetingProcessingService meetingProcessingService,
            IFileValidationService fileValidationService,
            IFileService fileService,
            IMeetingNoteGenerationService noteGenerationService)
        {
            _meetingProcessingService = meetingProcessingService;
            _fileValidationService = fileValidationService;
            _fileService = fileService;
            _noteGenerationService = noteGenerationService;

            // Initialize commands
            SelectAudioFileCommand = new AsyncRelayCommand(SelectAudioFileAsync);
            ProcessMeetingCommand = new AsyncRelayCommand(ProcessMeetingAsync, CanExecuteProcessMeeting);
            SelectWhisperModelCommand = new AsyncRelayCommand(SelectWhisperModelAsync);
            SelectSystemPromptCommand = new AsyncRelayCommand(SelectSystemPromptAsync);

            // Initialize available models
            LoadModelsAsync();
        }

        #region Properties

        public ICommand SelectAudioFileCommand { get; }
        public ICommand ProcessMeetingCommand { get; }
        public ICommand SelectWhisperModelCommand { get; }
        public ICommand SelectSystemPromptCommand { get; }

        public string SelectedAudioFile
        {
            get => _selectedAudioFile;
            set
            {
                if (SetProperty(ref _selectedAudioFile, value))
                {
                    ((AsyncRelayCommand)ProcessMeetingCommand).NotifyCanExecuteChanged();
                }
            }
        }

        public string SelectedModel
        {
            get => _selectedModel;
            set => SetProperty(ref _selectedModel, value);
        }

        public string SelectedWhisperModelPath
        {
            get => _selectedWhisperModelPath;
            set
            {
                if (SetProperty(ref _selectedWhisperModelPath, value))
                {
                    ((AsyncRelayCommand)ProcessMeetingCommand).NotifyCanExecuteChanged();
                }
            }
        }

        public string SelectedSystemPromptPath
        {
            get => _selectedSystemPromptPath;
            set
            {
                if (SetProperty(ref _selectedSystemPromptPath, value))
                {
                    ((AsyncRelayCommand)ProcessMeetingCommand).NotifyCanExecuteChanged();
                }
            }
        }

        public string ProgressText
        {
            get => _progressText;
            set => SetProperty(ref _progressText, value);
        }

        public int ProgressValue
        {
            get => _progressValue;
            set => SetProperty(ref _progressValue, value);
        }

        public bool IsProcessing
        {
            get => _isProcessing;
            set
            {
                if (SetProperty(ref _isProcessing, value))
                {
                    // Notify commands that their can-execute status may have changed
                    ((AsyncRelayCommand)ProcessMeetingCommand).NotifyCanExecuteChanged();
                }
            }
        }

        public string StatusMessage
        {
            get => _statusMessage;
            set => SetProperty(ref _statusMessage, value);
        }

        public ObservableCollection<string> AvailableModels
        {
            get => _availableModels;
            set => SetProperty(ref _availableModels, value);
        }

        public string TranscriptPreview
        {
            get => _transcriptPreview;
            set => SetProperty(ref _transcriptPreview, value);
        }

        #endregion

        #region Command Methods

        private async Task SelectAudioFileAsync()
        {
            var openFileDialog = new Microsoft.Win32.OpenFileDialog
            {
                Filter = "Audio Files|*.mp3;*.wav;*.flac;*.m4a|MP3 Files (*.mp3)|*.mp3|WAV Files (*.wav)|*.wav|FLAC Files (*.flac)|*.flac|M4A Files (*.m4a)|*.m4a|All Files (*.*)|*.*"
            };

            if (openFileDialog.ShowDialog() == true)
            {
                SelectedAudioFile = openFileDialog.FileName;
            }
        }

        private async Task ProcessMeetingAsync()
        {
            if (string.IsNullOrEmpty(SelectedAudioFile))
            {
                StatusMessage = "Please select an audio file first.";
                return;
            }

            if (string.IsNullOrEmpty(SelectedWhisperModelPath))
            {
                StatusMessage = "Please select a Whisper model file.";
                return;
            }

            if (string.IsNullOrEmpty(SelectedSystemPromptPath))
            {
                StatusMessage = "Please select a system prompt file.";
                return;
            }

            if (string.IsNullOrEmpty(SelectedModel))
            {
                StatusMessage = "Please select an Ollama model.";
                return;
            }

            IsProcessing = true;
            ProgressText = "Validating files...";
            ProgressValue = 0;

            try
            {
                // Validate files
                var isValidAudio = await _fileValidationService.ValidateAudioFileAsync(SelectedAudioFile);
                if (!isValidAudio)
                {
                    StatusMessage = "Invalid audio file. Please select a supported format (MP3, WAV, FLAC, M4A) under the size limit.";
                    return;
                }

                var isValidModel = await _fileValidationService.ValidateWhisperModelExistsAsync(SelectedWhisperModelPath);
                if (!isValidModel)
                {
                    StatusMessage = "Invalid or missing Whisper model file. Please select a valid .bin file.";
                    return;
                }

                var isValidPrompt = await _fileValidationService.ValidateSystemPromptExistsAsync(SelectedSystemPromptPath);
                if (!isValidPrompt)
                {
                    StatusMessage = "Invalid or missing system prompt file. Please select a valid .txt file.";
                    return;
                }

                // Prepare request
                var request = new ProcessMeetingRequestDto
                {
                    AudioFilePath = SelectedAudioFile,
                    WhisperModelPath = SelectedWhisperModelPath,
                    SystemPromptPath = SelectedSystemPromptPath,
                    OllamaModelName = SelectedModel
                };

                // Create progress reporter
                var progress = new Progress<TranscriptionProgressDto>(progressDto =>
                {
                    ProgressValue = progressDto.Percentage;
                    ProgressText = progressDto.StatusMessage;
                });

                // Process the meeting
                var response = await _meetingProcessingService.ProcessMeetingAsync(request, progress);

                if (response.Success)
                {
                    StatusMessage = $"Processing completed successfully in {response.ProcessingTimeMs}ms";
                    ProgressText = "Processing complete!";
                    ProgressValue = 100;

                    // Update transcript preview with information about the output
                    TranscriptPreview = $"Processing complete. Transcript and notes saved to Output folder:\nTranscript: {Path.GetFileName(response.TranscriptFilePath)}\nNotes: {Path.GetFileName(response.PdfFilePath)}";
                }
                else
                {
                    StatusMessage = $"Error: {response.Message}";
                }
            }
            catch (Exception ex)
            {
                StatusMessage = $"Unexpected error: {ex.Message}";
            }
            finally
            {
                IsProcessing = false;
            }
        }

        private bool CanExecuteProcessMeeting()
        {
            return !string.IsNullOrEmpty(SelectedAudioFile) &&
                   !string.IsNullOrEmpty(SelectedWhisperModelPath) &&
                   !string.IsNullOrEmpty(SelectedSystemPromptPath) &&
                   !IsProcessing;
        }

        private async Task SelectWhisperModelAsync()
        {
            var openFileDialog = new Microsoft.Win32.OpenFileDialog
            {
                Filter = "Model Files|*.bin|BIN Files (*.bin)|*.bin|All Files (*.*)|*.*"
            };

            if (openFileDialog.ShowDialog() == true)
            {
                SelectedWhisperModelPath = openFileDialog.FileName;
            }
        }

        private async Task SelectSystemPromptAsync()
        {
            var openFileDialog = new Microsoft.Win32.OpenFileDialog
            {
                Filter = "Text Files|*.txt|TXT Files (*.txt)|*.txt|All Files (*.*)|*.*"
            };

            if (openFileDialog.ShowDialog() == true)
            {
                SelectedSystemPromptPath = openFileDialog.FileName;
            }
        }

        #endregion

        #region Helper Methods

        private async void LoadModelsAsync()
        {
            try
            {
                var models = await _noteGenerationService.GetAvailableModelsAsync();
                AvailableModels.Clear();
                foreach (var model in models)
                {
                    AvailableModels.Add(model);
                }

                if (AvailableModels.Count > 0)
                {
                    SelectedModel = AvailableModels[0];
                }
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error loading models: {ex.Message}";
            }
        }

        #endregion
    }

    #region Command Implementation

    public class AsyncRelayCommand : ICommand
    {
        private readonly Func<Task> _execute;
        private readonly Func<bool>? _canExecute;
        private bool _isExecuting;

        public AsyncRelayCommand(Func<Task> execute, Func<bool>? canExecute = null)
        {
            _execute = execute ?? throw new ArgumentNullException(nameof(execute));
            _canExecute = canExecute;
        }

        public event EventHandler? CanExecuteChanged;

        public bool CanExecute(object? parameter)
        {
            return !_isExecuting && (_canExecute?.Invoke() ?? true);
        }

        public async void Execute(object? parameter)
        {
            _isExecuting = true;
            try
            {
                RaiseCanExecuteChanged();
                await _execute();
            }
            finally
            {
                _isExecuting = false;
                RaiseCanExecuteChanged();
            }
        }

        public void NotifyCanExecuteChanged()
        {
            RaiseCanExecuteChanged();
        }

        private void RaiseCanExecuteChanged()
        {
            CanExecuteChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    public class AsyncRelayCommand<T> : ICommand
    {
        private readonly Func<T?, Task> _execute;
        private readonly Predicate<T?>? _canExecute;
        private bool _isExecuting;

        public AsyncRelayCommand(Func<T?, Task> execute, Predicate<T?>? canExecute = null)
        {
            _execute = execute ?? throw new ArgumentNullException(nameof(execute));
            _canExecute = canExecute;
        }

        public event EventHandler? CanExecuteChanged;

        public bool CanExecute(object? parameter)
        {
            return !_isExecuting && (_canExecute?.Invoke((T?)parameter) ?? true);
        }

        public async void Execute(object? parameter)
        {
            _isExecuting = true;
            try
            {
                RaiseCanExecuteChanged();
                await _execute((T?)parameter);
            }
            finally
            {
                _isExecuting = false;
                RaiseCanExecuteChanged();
            }
        }

        public void NotifyCanExecuteChanged()
        {
            RaiseCanExecuteChanged();
        }

        private void RaiseCanExecuteChanged()
        {
            CanExecuteChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    #endregion
}