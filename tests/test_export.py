import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QTextTable  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from meeting_notes.export.pdf import build_document  # noqa: E402
from meeting_notes.export.writer import OutputPaths, write_pdf, write_text  # noqa: E402

_app = QApplication.instance() or QApplication([])


class PdfDocumentTests(unittest.TestCase):
    def test_title_subtitle_and_content(self):
        document = build_document("# Overview\n- **bold** item", subtitle="standup.mp4")
        lines = document.toPlainText().splitlines()
        self.assertEqual(lines[:4], ["Meeting Notes", "standup.mp4", "Overview", "bold item"])

    def test_angle_brackets_and_tasks_are_kept_as_text(self):
        text = build_document("- [ ] Review <draft>\n- [x] Done\n\nAfter").toPlainText()
        self.assertIn("☐ Review <draft>", text)
        self.assertIn("☑ Done", text)
        self.assertIn("After", text)

    def test_code_is_left_untouched(self):
        text = build_document("Use `a<b>` here\n\n```\nx < y\n```").toPlainText()
        self.assertIn("Use a<b> here", text)
        self.assertIn("x < y", text)

    def test_tables_are_created(self):
        document = build_document("| A | B |\n|---|---|\n| 1 | 2 |")
        frames = document.rootFrame().childFrames()
        tables = [frame for frame in frames if isinstance(frame, QTextTable)]
        self.assertEqual(len(tables), 1)
        self.assertEqual((tables[0].rows(), tables[0].columns()), (2, 2))


class WriterTests(unittest.TestCase):
    def test_output_paths_share_timestamp(self):
        paths = OutputPaths.for_media("standup.mp4", Path("out"), datetime(2024, 1, 2, 3, 4, 5))
        self.assertEqual(paths.transcript.name, "standup_2024-01-02_03-04-05_transcript.txt")
        self.assertEqual(paths.notes_markdown.name, "standup_2024-01-02_03-04-05_notes.md")
        self.assertEqual(paths.notes_pdf.name, "standup_2024-01-02_03-04-05_notes.pdf")
        self.assertEqual(paths.subtitles_srt.name, "standup_2024-01-02_03-04-05.srt")
        self.assertEqual(paths.subtitles_vtt.name, "standup_2024-01-02_03-04-05.vtt")

    def test_output_paths_never_overwrite(self):
        moment = datetime(2024, 1, 2, 3, 4, 5)
        with tempfile.TemporaryDirectory() as tmp:
            first = OutputPaths.for_media("a.mp3", Path(tmp), moment)
            write_text(first.transcript, "x")
            second = OutputPaths.for_media("a.mp3", Path(tmp), moment)
            self.assertEqual(second.transcript.name, "a_2024-01-02_03-04-05_2_transcript.txt")

    def test_writes_text_and_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested"
            write_text(target / "a.txt", "héllo")
            write_pdf(target / "a.pdf", "# Notes\n- point & detail", "meeting.mp3")
            self.assertEqual((target / "a.txt").read_text(encoding="utf-8"), "héllo")
            self.assertTrue((target / "a.pdf").read_bytes().startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
