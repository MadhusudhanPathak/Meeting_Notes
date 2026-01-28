using System;
using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using MeetingNotesMaker.Presentation.ViewModels;
using MeetingNotesMaker.Application.Services;
using MeetingNotesMaker.Infrastructure.Services;
using MeetingNotesMaker.Infrastructure.Logging;
using MeetingNotesMaker.Infrastructure.Configuration;
using MeetingNotesMaker.Domain.Services;
using System.IO;

namespace MeetingNotesMaker
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            try
            {
                // Initialize logging
                LoggerSetup.ConfigureLogger();

                InitializeComponent();

                // Set up dependency injection container
                var serviceProvider = ConfigureServices();

                // Get the main view model and set it as the data context
                var mainViewModel = serviceProvider.GetRequiredService<MainViewModel>();
                DataContext = mainViewModel;
            }
            catch (Exception ex)
            {
                // Log the exception
                Serilog.Log.Logger.Error(ex, "Failed to initialize MainWindow");

                // Show error to user
                System.Windows.MessageBox.Show($"Failed to start the application: {ex.Message}",
                    "Application Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);

                // Close the application
                Close();
            }
        }

        private IServiceProvider ConfigureServices()
        {
            var builder = new ConfigurationBuilder()
                .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
                .AddEnvironmentVariables();

            var configuration = builder.Build();

            var services = new ServiceCollection();

            // Register configuration
            services.AddSingleton<IConfiguration>(configuration);
            services.AddAppConfiguration(configuration);
            services.Configure<AppSettings>(configuration.GetSection(AppSettings.SectionName));

            // Register logging
            services.AddLogging(configure => configure
                .AddConsole()
                .AddDebug());

            // Register application services
            services.AddScoped<IMeetingProcessingService, MeetingProcessingService>();

            // Register infrastructure services
            services.AddScoped<IAudioTranscriptionService, WhisperService>();
            services.AddScoped<IMeetingNoteGenerationService>(serviceProvider =>
            {
                var configuration = serviceProvider.GetRequiredService<IConfiguration>();
                var logger = serviceProvider.GetRequiredService<ILogger<OllamaService>>();
                var apiUrl = configuration.GetSection(AppSettings.SectionName)["OllamaApiUrl"] ?? "http://localhost:11434";
                return new OllamaService(apiUrl, logger);
            });
            services.AddScoped<IPdfGenerationService, PdfGenerationService>();
            services.AddScoped<IFileService, FileService>();
            services.AddScoped<IFileValidationService, FileValidationService>();

            // Register view models
            services.AddTransient<MainViewModel>();

            return services.BuildServiceProvider();
        }
    }
}