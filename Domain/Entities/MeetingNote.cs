using System;

namespace MeetingNotesMaker.Domain.Entities
{
    public class MeetingNote
    {
        public string Title { get; set; } = string.Empty;
        public DateTime GeneratedAt { get; set; } = DateTime.UtcNow;
        public string KeyDiscussionPoints { get; set; } = string.Empty;
        public string DecisionsMade { get; set; } = string.Empty;
        public string ActionItems { get; set; } = string.Empty;
        public string Deadlines { get; set; } = string.Empty;
        public string QuestionsAndAnswers { get; set; } = string.Empty;
        public string RawTranscript { get; set; } = string.Empty;
        
        public MeetingNote Normalize()
        {
            Title = Title?.Trim() ?? string.Empty;
            KeyDiscussionPoints = KeyDiscussionPoints?.Trim() ?? string.Empty;
            DecisionsMade = DecisionsMade?.Trim() ?? string.Empty;
            ActionItems = ActionItems?.Trim() ?? string.Empty;
            Deadlines = Deadlines?.Trim() ?? string.Empty;
            QuestionsAndAnswers = QuestionsAndAnswers?.Trim() ?? string.Empty;
            RawTranscript = RawTranscript?.Trim() ?? string.Empty;
            
            return this;
        }
    }
}