using System;

namespace MeetingNotesMaker.Domain.Entities
{
    public class TranscriptionResult
    {
        public string FullText { get; set; } = string.Empty;
        public List<TranscriptionSegment> Segments { get; set; } = new List<TranscriptionSegment>();
        public TimeSpan Duration { get; set; }
        public string FileName { get; set; } = string.Empty;
        
        public TranscriptionResult Normalize()
        {
            FullText = FullText?.Trim() ?? string.Empty;
            FileName = FileName?.Trim() ?? string.Empty;
            Segments = Segments ?? new List<TranscriptionSegment>();
            
            return this;
        }
    }

    public class TranscriptionSegment
    {
        public TimeSpan StartTime { get; set; }
        public TimeSpan EndTime { get; set; }
        public string Text { get; set; } = string.Empty;
        
        public TranscriptionSegment Normalize()
        {
            Text = Text?.Trim() ?? string.Empty;
            
            return this;
        }
    }
}