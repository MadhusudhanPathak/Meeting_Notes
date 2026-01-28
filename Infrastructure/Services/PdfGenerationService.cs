using System;
using System.IO;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;
using Microsoft.Extensions.Logging;
using MeetingNotesMaker.Domain.Entities;

namespace MeetingNotesMaker.Infrastructure.Services
{
    public interface IPdfGenerationService
    {
        Task<byte[]> GenerateMeetingNotesPdfAsync(MeetingNote meetingNote);
        Task SaveMeetingNotesPdfAsync(MeetingNote meetingNote, string outputPath);
    }

    public class PdfGenerationService : IPdfGenerationService
    {
        private readonly ILogger<PdfGenerationService> _logger;

        public PdfGenerationService(ILogger<PdfGenerationService> logger)
        {
            _logger = logger;
            // Configure QuestPDF
            QuestPDF.Settings.License = LicenseType.Community;
        }

        public async Task<byte[]> GenerateMeetingNotesPdfAsync(MeetingNote meetingNote)
        {
            try
            {
                _logger.LogInformation("Starting PDF generation for meeting note: {Title}", meetingNote.Title);

                var document = Document.Create(container =>
                {
                    container.Page(page =>
                    {
                        page.Size(PageSizes.A4);
                        page.Margin(2, Unit.Centimetre);
                        page.DefaultTextStyle(x => x.FontSize(12));

                        page.Header()
                            .Text($"Meeting Notes - {meetingNote.Title}")
                            .SemiBold().FontSize(20).FontColor(Colors.Blue.Medium);

                        page.Content()
                            .PaddingVertical(1, Unit.Centimetre)
                            .Column(x =>
                            {
                                x.Item().Element(BuildGeneratedAtInfo);
                                x.Item().Element(BuildKeyDiscussionPoints);
                                x.Item().Element(BuildDecisionsMade);
                                x.Item().Element(BuildActionItems);
                                x.Item().Element(BuildDeadlines);
                                x.Item().Element(BuildQuestionsAndAnswers);
                            });

                        page.Footer()
                            .AlignCenter()
                            .Text($"Generated on {meetingNote.GeneratedAt:yyyy-MM-dd HH:mm:ss}");
                    });

                    void BuildGeneratedAtInfo(IContainer container)
                    {
                        container.Background(Colors.Grey.Lighten2)
                            .Padding(10)
                            .Text($"Generated at: {meetingNote.GeneratedAt:yyyy-MM-dd HH:mm:ss}")
                            .SemiBold();
                    }

                    void BuildKeyDiscussionPoints(IContainer container)
                    {
                        if (!string.IsNullOrWhiteSpace(meetingNote.KeyDiscussionPoints))
                        {
                            container.PaddingVertical(5)
                                .Column(x =>
                                {
                                    x.Item().Element(container => BuildHeading(container, "Key Discussion Points"));
                                    x.Item().PaddingTop(5).Text(meetingNote.KeyDiscussionPoints);
                                });
                        }
                    }

                    void BuildDecisionsMade(IContainer container)
                    {
                        if (!string.IsNullOrWhiteSpace(meetingNote.DecisionsMade))
                        {
                            container.PaddingVertical(5)
                                .Column(x =>
                                {
                                    x.Item().Element(container => BuildHeading(container, "Decisions Made"));
                                    x.Item().PaddingTop(5).Text(meetingNote.DecisionsMade);
                                });
                        }
                    }

                    void BuildActionItems(IContainer container)
                    {
                        if (!string.IsNullOrWhiteSpace(meetingNote.ActionItems))
                        {
                            container.PaddingVertical(5)
                                .Column(x =>
                                {
                                    x.Item().Element(container => BuildHeading(container, "Action Items"));
                                    x.Item().PaddingTop(5).Text(meetingNote.ActionItems);
                                });
                        }
                    }

                    void BuildDeadlines(IContainer container)
                    {
                        if (!string.IsNullOrWhiteSpace(meetingNote.Deadlines))
                        {
                            container.PaddingVertical(5)
                                .Column(x =>
                                {
                                    x.Item().Element(container => BuildHeading(container, "Deadlines"));
                                    x.Item().PaddingTop(5).Text(meetingNote.Deadlines);
                                });
                        }
                    }

                    void BuildQuestionsAndAnswers(IContainer container)
                    {
                        if (!string.IsNullOrWhiteSpace(meetingNote.QuestionsAndAnswers))
                        {
                            container.PaddingVertical(5)
                                .Column(x =>
                                {
                                    x.Item().Element(container => BuildHeading(container, "Questions and Answers"));
                                    x.Item().PaddingTop(5).Text(meetingNote.QuestionsAndAnswers);
                                });
                        }
                    }

                    IContainer BuildHeading(IContainer container, string title)
                    {
                        container
                            .BorderBottom(1).BorderColor(Colors.Black)
                            .PaddingBottom(5)
                            .Text(title)
                            .SemiBold();
                        return container;
                    }
                });

                var pdfBytes = document.GeneratePdf();
                _logger.LogInformation("Completed PDF generation for meeting note: {Title}", meetingNote.Title);
                
                return pdfBytes;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error generating PDF for meeting note: {Title}", meetingNote.Title);
                throw;
            }
        }

        public async Task SaveMeetingNotesPdfAsync(MeetingNote meetingNote, string outputPath)
        {
            try
            {
                _logger.LogInformation("Saving PDF to path: {Path}", outputPath);
                
                var pdfBytes = await GenerateMeetingNotesPdfAsync(meetingNote);
                await File.WriteAllBytesAsync(outputPath, pdfBytes);
                
                _logger.LogInformation("Successfully saved PDF to path: {Path}", outputPath);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error saving PDF to path: {Path}", outputPath);
                throw;
            }
        }
    }
}