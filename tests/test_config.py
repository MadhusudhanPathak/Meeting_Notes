import tempfile
import unittest
from pathlib import Path

from meeting_notes.config import AppConfig


class AppConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.resources = self.root / "resources"

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, *names):
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    def _discover(self, windows=True):
        return AppConfig.discover(self.root, self.resources, windows=windows)

    def test_missing_everything_reports_all_errors(self):
        config = self._discover()
        self.assertEqual(len(config.transcription_errors()), 3)
        self.assertEqual(len(config.prompt_errors()), 1)
        self.assertTrue(any(line.startswith("INFO:") for line in config.validate()))

    def test_complete_setup_is_valid(self):
        self._touch("Whisper.exe", "Whisper.dll", "input/b.bin", "input/A.bin", "input/prompt.txt")
        config = self._discover()
        self.assertEqual(config.validate(), [])
        self.assertEqual([path.name for path in config.model_paths], ["A.bin", "b.bin"])

    def test_builtin_prompt_satisfies_prompt_requirement(self):
        self._touch("resources/prompts/Default.txt", "input/mine.txt")
        config = self._discover()
        self.assertEqual(config.prompt_errors(), [])
        self.assertEqual([path.name for path in config.prompt_paths], ["mine.txt", "Default.txt"])
        self.assertTrue(config.is_builtin_prompt(config.prompt_paths[1]))
        self.assertFalse(config.is_builtin_prompt(config.prompt_paths[0]))

    def test_partial_downloads_are_not_models(self):
        self._touch("input/ggml-small.bin.part")
        self.assertEqual(self._discover().model_paths, ())

    def test_non_windows_uses_whisper_cpp_from_app_folder(self):
        self._touch("whisper-cli", "input/m.bin")
        config = self._discover(windows=False)
        self.assertEqual(config.whisper_exe, self.root / "whisper-cli")
        self.assertIsNone(config.whisper_dll)
        self.assertEqual(config.transcription_errors(), [])

    def test_non_windows_reports_missing_whisper_cpp_and_ffmpeg(self):
        config = AppConfig(self.root / "input", self.root / "output", None, windows=False)
        self.assertIn("whisper-cli", config.transcription_errors()[0])
        self.assertIn("ffmpeg", config.warnings()[0])
        self.assertEqual(self._discover().warnings(), [])

    def test_ensure_directories_creates_folders(self):
        config = self._discover()
        config.ensure_directories()
        self.assertTrue(config.input_dir.is_dir())
        self.assertTrue(config.output_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
