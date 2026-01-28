using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace MeetingNotesMaker.Infrastructure.Configuration
{
    public class AppSettings
    {
        public const string SectionName = "AppSettings";

        public string OllamaApiUrl { get; set; } = "http://localhost:11434";
        public string OllamaDefaultModel { get; set; } = "llama2";
        public string DefaultWorkingDirectory { get; set; } = string.Empty;
        public int MaxFileSizeMB { get; set; } = 100;
        public int TranscriptionTimeoutSeconds { get; set; } = 300;
        public string WhisperModelPath { get; set; } = "./Models/";
        public string WhisperDefaultLanguage { get; set; } = "en";
    }

    public static class ConfigurationExtensions
    {
        public static IServiceCollection AddAppConfiguration(this IServiceCollection services, IConfiguration configuration)
        {
            services.Configure<AppSettings>(configuration.GetSection(AppSettings.SectionName));
            return services;
        }
    }
}