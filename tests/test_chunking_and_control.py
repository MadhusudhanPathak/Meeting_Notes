import threading
import time
import unittest

from meeting_notes.core.chunking import estimate_tokens, round_up, split_text
from meeting_notes.core.control import JobCancelled, JobControl


class ChunkingTests(unittest.TestCase):
    def test_non_latin_text_is_estimated_conservatively(self):
        self.assertGreater(estimate_tokens("नमस्ते दुनिया"), estimate_tokens("hello world!"))

    def test_round_up(self):
        self.assertEqual(round_up(4097, 1024), 5120)
        self.assertEqual(round_up(4096, 1024), 4096)

    def test_split_keeps_every_line_and_respects_budget(self):
        lines = [f"[00:00:{i:02d}.000 --> 00:00:{i:02d}.500]  line {i} " * 2 for i in range(60)]
        chunks = split_text("\n".join(lines), 200)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(estimate_tokens(chunk), 200 + len(chunk.splitlines()))
        self.assertEqual("\n".join(chunks).splitlines(), lines)

    def test_split_breaks_overlong_lines(self):
        chunks = split_text("word " * 500, 50)
        self.assertGreater(len(chunks), 5)
        self.assertEqual(" ".join(chunks).split(), ["word"] * 500)


class JobControlTests(unittest.TestCase):
    def test_pause_blocks_until_resume(self):
        control = JobControl()
        control.pause()
        passed = threading.Event()
        threading.Thread(target=lambda: (control.checkpoint(), passed.set()), daemon=True).start()
        time.sleep(0.1)
        self.assertFalse(passed.is_set())
        control.resume()
        self.assertTrue(passed.wait(1))

    def test_cancel_releases_paused_checkpoint(self):
        control = JobControl()
        control.pause()
        errors = []

        def wait():
            try:
                control.checkpoint()
            except JobCancelled:
                errors.append("cancelled")

        thread = threading.Thread(target=wait)
        thread.start()
        control.cancel()
        thread.join(1)
        self.assertEqual(errors, ["cancelled"])

    def test_hooks_run_and_apply_current_state(self):
        calls = []
        control = JobControl()
        control.pause()
        with control.attach(pause=lambda: calls.append("pause"),
                            resume=lambda: calls.append("resume"),
                            abort=lambda: calls.append("abort")):
            control.resume()
            control.cancel()
        control.cancel()
        self.assertEqual(calls, ["pause", "resume", "abort"])


if __name__ == "__main__":
    unittest.main()
