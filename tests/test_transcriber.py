import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from meeting_notes.core.control import JobCancelled, JobControl
from meeting_notes.core.transcriber import (
    AudioTranscriber,
    Transcript,
    TranscriptionError,
    TranscriptionOptions,
    WhisperEngine,
    is_supported_media_file,
    segment_end_seconds,
    srt_to_timestamped_text,
)

TXT = (
    "\ufeff[00:00:00.000 --> 00:00:03.760]  Good morning.\n"
    "[00:00:03.760 --> 00:01:08.560]  Next item.\n"
)
SRT = "\ufeff1\n00:00:00,000 --> 00:00:03,760\nGood morning.\n"
VTT = "\ufeffWEBVTT\n\n00:00:00.000 --> 00:00:03.760\nGood morning.\n"


class FakeProcess:
    """Stands in for Whisper.exe: writes its outputs next to the input file."""

    def __init__(self, command, returncode=0, write_outputs=True, stderr=b""):
        self.command = command
        self.pid = 0
        self.returncode = returncode
        if Path(command[0]).stem == "ffmpeg":
            Path(command[-1]).write_bytes(b"RIFF")
            write_outputs = False
            media = None
        else:
            media = Path(command[command.index("-f") + 1])
        if write_outputs:
            for suffix, text in ((".txt", TXT), (".srt", SRT), (".vtt", VTT)):
                media.with_suffix(suffix).write_text(text, encoding="utf-8")
        self.stdout = io.BytesIO(
            b"[00:00:00.000 --> 00:00:03.760]   Good morning.\r\n"
            b"[00:00:03.760 --> 00:01:08.560]   Next item.\r\n"
        )
        self.stderr = io.BytesIO(stderr)

    def wait(self):
        return self.returncode

    def kill(self):
        self.returncode = 1


class _TranscriberTestCase(unittest.TestCase):
    """Temporary folder with fake engine binaries, a model, and media files."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.exe = root / "Whisper.exe"
        self.model = root / "model.bin"
        self.media = root / "My Meeting.mp4"
        for path in (self.exe, self.model, self.media):
            path.touch()
        self.transcriber = AudioTranscriber(self.exe, self.model)
        self.commands = []

    def tearDown(self):
        self._tmp.cleanup()

    def _patch(self, **kwargs):
        def popen(command, **_):
            self.commands.append(command)
            return FakeProcess(command, **kwargs)

        return mock.patch("meeting_notes.core.transcriber.subprocess.Popen", side_effect=popen)


class ConstMeTranscriberTests(_TranscriberTestCase):
    """Const-me's Whisper.exe, used on Windows."""

    def test_supported_extensions_include_video(self):
        self.assertTrue(is_supported_media_file("a.MP3"))
        self.assertTrue(is_supported_media_file("clip.mkv"))
        self.assertFalse(is_supported_media_file("a.txt"))
        self.assertFalse(is_supported_media_file("voice.ogg"))

    def test_segment_end_seconds(self):
        self.assertEqual(segment_end_seconds("[00:01:02.500 --> 01:00:03.250]  hi"), 3603.25)
        self.assertIsNone(segment_end_seconds("Loaded model"))

    def test_success_reads_all_formats_and_reports_progress(self):
        progress = []
        with self._patch():
            transcript = self.transcriber.transcribe(
                self.media, TranscriptionOptions(language="hi", translate=True, gpu="GPU 1"),
                on_progress=progress.append,
            )
        self.assertEqual(progress, [3.76, 68.56])
        self.assertTrue(transcript.timestamped_text.startswith("[00:00:00.000"))
        self.assertTrue(transcript.srt.startswith("1\n"))
        self.assertTrue(transcript.vtt.startswith("WEBVTT"))
        command = self.commands[0]
        self.assertEqual(command[command.index("-l") + 1], "hi")
        self.assertIn("-tr", command)
        self.assertEqual(command[command.index("-gpu") + 1], "GPU 1")

    def test_runs_on_private_copy_and_leaves_source_folder_untouched(self):
        with self._patch():
            self.transcriber.transcribe(self.media)
        staged = Path(self.commands[0][self.commands[0].index("-f") + 1])
        self.assertNotEqual(staged.parent, self.media.parent)
        self.assertFalse(staged.parent.exists())
        self.assertEqual(sorted(p.name for p in self.media.parent.iterdir()),
                         ["My Meeting.mp4", "Whisper.exe", "model.bin"])

    def test_nonzero_exit_raises_with_stderr(self):
        with self._patch(returncode=1, write_outputs=False, stderr=b"bad model"):
            with self.assertRaisesRegex(TranscriptionError, "bad model"):
                self.transcriber.transcribe(self.media)

    def test_missing_output_raises(self):
        with self._patch(write_outputs=False):
            with self.assertRaisesRegex(TranscriptionError, "output file not found"):
                self.transcriber.transcribe(self.media)

    def test_cancelled_control_raises(self):
        control = JobControl()
        control.cancel()
        with self._patch():
            with self.assertRaises(JobCancelled):
                self.transcriber.transcribe(self.media, control=control)


class WhisperCppTranscriberTests(_TranscriberTestCase):
    """whisper.cpp's whisper-cli, used on Linux and macOS."""

    def setUp(self):
        super().setUp()
        root = self.exe.parent
        self.cli = root / "whisper-cli"
        self.ffmpeg = root / "ffmpeg"
        self.audio = root / "talk.mp3"
        for path in (self.cli, self.ffmpeg, self.audio):
            path.touch()

    def test_uses_output_prefix_and_builds_timestamps_from_srt(self):
        with self._patch():
            transcript = AudioTranscriber(self.cli, self.model).transcribe(
                self.audio, TranscriptionOptions(gpu="ignored")
            )
        command = self.commands[0]
        self.assertEqual(AudioTranscriber(self.cli, self.model).engine, WhisperEngine.WHISPER_CPP)
        self.assertIn("-of", command)
        self.assertNotIn("-nc", command)
        self.assertNotIn("-gpu", command)
        self.assertEqual(
            transcript.timestamped_text, "[00:00:00.000 --> 00:00:03.760]  Good morning."
        )

    def test_video_is_converted_with_ffmpeg(self):
        with self._patch():
            AudioTranscriber(self.cli, self.model, self.ffmpeg).transcribe(self.media)
        self.assertEqual(Path(self.commands[0][0]).name, "ffmpeg")
        whisper_input = Path(self.commands[1][self.commands[1].index("-f") + 1])
        self.assertEqual(whisper_input.suffix, ".wav")

    def test_video_without_ffmpeg_explains_what_to_install(self):
        with self._patch():
            with self.assertRaisesRegex(TranscriptionError, "Install ffmpeg"):
                AudioTranscriber(self.cli, self.model).transcribe(self.media)


class TranscriptTests(unittest.TestCase):
    def test_srt_conversion(self):
        srt = (
            "1\r\n00:00:01,500 --> 01:02:03,004\r\nHello\r\nthere\r\n\r\n"
            "2\n00:00:04,000 --> 00:00:05,000\nBye\n"
        )
        self.assertEqual(
            srt_to_timestamped_text(srt),
            "[00:00:01.500 --> 01:02:03.004]  Hello there\n"
            "[00:00:04.000 --> 00:00:05.000]  Bye",
        )

    def test_text_with_and_without_timestamps(self):
        transcript = Transcript(timestamped_text=TXT.lstrip("\ufeff"), srt=SRT, vtt=VTT)
        self.assertEqual(transcript.plain_text(), "Good morning.\nNext item.")
        self.assertIn("[00:00:03.760 --> 00:01:08.560]", transcript.text(include_timestamps=True))


if __name__ == "__main__":
    unittest.main()
