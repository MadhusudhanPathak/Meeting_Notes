using Serilog;
using Microsoft.Extensions.Logging;

namespace MeetingNotesMaker.Infrastructure.Logging
{
    public static class LoggerSetup
    {
        public static void ConfigureLogger()
        {
            Log.Logger = new LoggerConfiguration()
                .MinimumLevel.Debug()
                .WriteTo.Console()
                .WriteTo.File("logs/meeting-notes-maker-.txt", rollingInterval: RollingInterval.Day)
                .CreateLogger();
        }

        // Removed the CreateLogger method as it's not needed for the static configuration
    }
}