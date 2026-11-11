import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from reportlab.platypus import Paragraph

from meeting_notes.export.pdf import build_story
from meeting_notes.export.writer import OutputPaths, write_pdf, write_text


def _paragraph_texts(markdown):
    return [flowable.text for flowable in build_story(markdown) if isinstance(flowable, Paragraph)]


class PdfStoryTests(unittest.TestCase):
    def test_headings_lists_and_inline_markup(self):
        texts = _paragraph_texts("# Title\n- **item**\n1. first\nUse `code` here")
        self.assertEqual(
            texts,
            [
                "Meeting Notes",
                "Title",
                "&bull; **item**",
                "1. first",
                'Use <font face="Courier">code</font> here',
            ],
        )

    def test_special_characters_are_escaped(self):
        self.assertIn("Q&amp;A &lt;5 min", _paragraph_texts("Q&A <5 min"))

    def test_malformed_markup_falls_back_to_plain_text(self):
        self.assertIn("**a _b** c_", _paragraph_texts("**a _b** c_"))

    def test_thematic_break_is_not_text(self):
        self.assertEqual(_paragraph_texts("---"), ["Meeting Notes"])


class WriterTests(unittest.TestCase):
    def test_output_paths_share_timestamp(self):
        paths = OutputPaths.for_audio("standup.mp3", Path("out"), datetime(2024, 1, 2, 3, 4, 5))
        self.assertEqual(paths.transcript.name, "standup_2024-01-02_03-04-05_transcript.txt")
        self.assertEqual(paths.notes_markdown.name, "standup_2024-01-02_03-04-05_notes.md")
        self.assertEqual(paths.notes_pdf.name, "standup_2024-01-02_03-04-05_notes.pdf")

    def test_writes_text_and_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested"
            write_text(target / "a.txt", "héllo")
            write_pdf(target / "a.pdf", "# Notes\n- point & detail")
            self.assertEqual((target / "a.txt").read_text(encoding="utf-8"), "héllo")
            self.assertTrue((target / "a.pdf").read_bytes().startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
