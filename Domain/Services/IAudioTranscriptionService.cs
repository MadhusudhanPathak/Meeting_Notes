using MeetingNotesMaker.Domain.Entities;

namespace MeetingNotesMaker.Domain.Services
{
    public interface IAudioTranscriptionService
    {
        Task<TranscriptionResult> TranscribeAudioAsync(string audioFilePath, string modelFilePath, IProgress<int>? progress = null);
        bool IsSupportedFormat(string fileName);
    }
}