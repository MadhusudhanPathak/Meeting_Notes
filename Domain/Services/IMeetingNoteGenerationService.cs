using MeetingNotesMaker.Domain.Entities;

namespace MeetingNotesMaker.Domain.Services
{
    public interface IMeetingNoteGenerationService
    {
        Task<MeetingNote> GenerateMeetingNotesAsync(string transcript, string systemPrompt, string modelName);
        Task<List<string>> GetAvailableModelsAsync();
    }
}