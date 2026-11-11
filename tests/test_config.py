import tempfile
import unittest
from pathlib import Path

from meeting_notes.config import AppConfig


class AppConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, *names):
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    def test_missing_everything_reports_all_errors(self):
        config = AppConfig.discover(self.root)
        self.assertEqual(len(config.transcription_errors()), 3)
        self.assertEqual(len(config.prompt_errors()), 1)
        self.assertTrue(any(line.startswith("INFO:") for line in config.validate()))

    def test_complete_setup_is_valid(self):
        self._touch("Whisper.exe", "Whisper.dll", "input/b.bin", "input/A.bin", "input/prompt.txt")
        config = AppConfig.discover(self.root)
        self.assertEqual(config.validate(), [])
        self.assertEqual([path.name for path in config.model_paths], ["A.bin", "b.bin"])

    def test_missing_prompt_does_not_block_transcription(self):
        self._touch("Whisper.exe", "Whisper.dll", "input/model.bin")
        config = AppConfig.discover(self.root)
        self.assertEqual(config.transcription_errors(), [])
        self.assertEqual(len(config.prompt_errors()), 1)

    def test_ensure_directories_creates_folders(self):
        config = AppConfig.discover(self.root)
        config.ensure_directories()
        self.assertTrue(config.input_dir.is_dir())
        self.assertTrue(config.output_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
