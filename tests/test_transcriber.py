import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from meeting_notes.core.transcriber import (
    AudioTranscriber,
    TranscriptionError,
    is_supported_audio_file,
)


class TranscriberTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.exe = root / "Whisper.exe"
        self.model = root / "model.bin"
        self.audio = root / "meeting.mp3"
        for path in (self.exe, self.model, self.audio):
            path.touch()
        self.transcriber = AudioTranscriber(self.exe, self.model)

    def tearDown(self):
        self._tmp.cleanup()

    def _fake_run(self, returncode=0, output_text=None, stderr=""):
        def run(command, **kwargs):
            if output_text is not None:
                self.audio.with_suffix(".txt").write_text(output_text, encoding="utf-8")
            return subprocess.CompletedProcess(command, returncode, "", stderr)

        return mock.patch("meeting_notes.core.transcriber.subprocess.run", side_effect=run)

    def test_supported_extensions(self):
        self.assertTrue(is_supported_audio_file("a.MP3"))
        self.assertFalse(is_supported_audio_file("a.txt"))

    def test_missing_model_raises(self):
        with self.assertRaises(FileNotFoundError):
            AudioTranscriber(self.exe, self.model.with_name("missing.bin"))

    def test_success_reads_and_removes_output(self):
        with self._fake_run(output_text="hello world"):
            self.assertEqual(self.transcriber.transcribe(self.audio), "hello world")
        self.assertFalse(self.audio.with_suffix(".txt").exists())

    def test_nonzero_exit_raises_with_stderr(self):
        with self._fake_run(returncode=1, stderr="bad model"):
            with self.assertRaisesRegex(TranscriptionError, "^Error during transcription: bad model$"):
                self.transcriber.transcribe(self.audio)

    def test_missing_output_raises(self):
        with self._fake_run():
            with self.assertRaisesRegex(TranscriptionError, "output file not found"):
                self.transcriber.transcribe(self.audio)


if __name__ == "__main__":
    unittest.main()
