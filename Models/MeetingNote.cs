using System;

namespace MeetingNotesMaker.Models
{
    public class MeetingNote
    {
        public string Title { get; set; } = string.Empty;
        public DateTime GeneratedAt { get; set; } = DateTime.Now;
        public string KeyDiscussionPoints { get; set; } = string.Empty;
        public string DecisionsMade { get; set; } = string.Empty;
        public string ActionItems { get; set; } = string.Empty;
        public string Deadlines { get; set; } = string.Empty;
        public string QuestionsAndAnswers { get; set; } = string.Empty;
        public string RawTranscript { get; set; } = string.Empty;
    }
}