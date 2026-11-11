import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import requests

from meeting_notes.core import note_generator as ng
from meeting_notes.core.control import JobCancelled, JobControl
from meeting_notes.core.note_generator import ModelInfo, NoteGenerationError, NoteGenerator


def _response(json_data=None, status=200):
    response = mock.Mock()
    response.json.return_value = json_data
    if status >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status} error")
    return response


class _FakeOllama(BaseHTTPRequestHandler):
    """Streams canned NDJSON replies and records request bodies."""

    replies = []
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append((self.path, body))
        status, lines = type(self).replies.pop(0)
        self.send_response(status)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        for line in lines:
            self.wfile.write((json.dumps(line) + "\n").encode())

    def log_message(self, *args):
        pass


class NoteGeneratorApiTests(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.generator = NoteGenerator(session=self.session)

    def test_lists_model_names(self):
        self.session.request.return_value = _response({"models": [{"name": "llama2"}]})
        self.assertEqual(self.generator.get_available_models(), ["llama2"])

    def test_connection_failure_is_wrapped(self):
        self.session.request.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaisesRegex(NoteGenerationError, "Cannot connect to Ollama"):
            self.generator.get_available_models()

    def test_invalid_models_payload(self):
        self.session.request.return_value = _response(["unexpected"])
        with self.assertRaises(NoteGenerationError):
            self.generator.get_available_models()

    def test_model_info_reads_context_and_thinking(self):
        self.session.request.return_value = _response({
            "model_info": {"gemma3.context_length": 131072, "gemma3.block_count": 34},
            "capabilities": ["completion", "thinking"],
        })
        self.assertEqual(self.generator.get_model_info("m"), ModelInfo(131072, True))

    def test_model_info_falls_back_when_unknown(self):
        self.session.request.return_value = _response({"details": {}})
        self.assertEqual(self.generator.get_model_info("m"), ModelInfo())


class GenerateNotesPlanningTests(unittest.TestCase):
    def setUp(self):
        self.generator = NoteGenerator(session=mock.Mock())
        self.calls = []

        def fake_generate(prompt, system, model, num_ctx, disable_thinking, control):
            self.calls.append((prompt, system, num_ctx))
            return f"summary {len(self.calls)}"

        self.generator._generate = fake_generate

    def _info(self, context_length):
        return mock.patch.object(
            self.generator, "get_model_info", return_value=ModelInfo(context_length)
        )

    def test_short_transcript_uses_one_call_with_sized_context(self):
        with self._info(131072):
            notes = self.generator.generate_notes("short transcript", "prompt", "m")
        self.assertEqual(notes, "summary 1")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][2], ng.MIN_CONTEXT_TOKENS + 1024)

    def test_long_transcript_is_summarised_in_parts_then_combined(self):
        transcript = "\n".join(f"Line {i}: " + "budget discussion " * 20 for i in range(400))
        statuses = []
        with self._info(8192):
            notes = self.generator.generate_notes(
                transcript, "MY PROMPT", "m", on_status=statuses.append
            )
        part_calls = [call for call in self.calls if call[1] == ng.PART_SYSTEM_PROMPT]
        self.assertGreater(len(part_calls), 1)
        self.assertEqual(self.calls[-1][1], "MY PROMPT")
        self.assertIn("summary 1", self.calls[-1][0])
        self.assertTrue(all(call[2] == 8192 for call in self.calls))
        self.assertEqual(notes, f"summary {len(self.calls)}")
        self.assertIn("parts first", statuses[0])

    def test_oversized_system_prompt_is_rejected(self):
        with self._info(4096):
            with self.assertRaisesRegex(NoteGenerationError, "system prompt is too long"):
                self.generator.generate_notes("t", "x " * 20000, "m")


class StreamingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOllama)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.generator = NoteGenerator(host=f"http://127.0.0.1:{cls.server.server_address[1]}")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        _FakeOllama.requests.clear()

    def test_generate_joins_stream_and_strips_thinking(self):
        _FakeOllama.replies = [(200, [
            {"response": "<think>hmm</think>## Notes"}, {"response": "\n- item"}, {"done": True},
        ])]
        text = self.generator._generate("t", "s", "m", 8192, True, None)
        self.assertEqual(text, "## Notes\n- item")
        path, body = _FakeOllama.requests[0]
        self.assertEqual(path, "/api/generate")
        self.assertEqual(body["options"], {"num_ctx": 8192})
        self.assertFalse(body["think"])

    def test_error_line_raises(self):
        _FakeOllama.replies = [(200, [{"error": "model not found"}])]
        with self.assertRaisesRegex(NoteGenerationError, "model not found"):
            self.generator._generate("t", "s", "m", 4096, False, None)

    def test_http_error_raises(self):
        _FakeOllama.replies = [(404, [{"error": "no such model"}])]
        with self.assertRaisesRegex(NoteGenerationError, "HTTP 404: no such model"):
            self.generator._generate("t", "s", "m", 4096, False, None)

    def test_pull_reports_progress(self):
        _FakeOllama.replies = [(200, [
            {"status": "pulling manifest"},
            {"status": "pulling abc", "completed": 5, "total": 10},
            {"status": "success"},
        ])]
        events = []
        self.generator.pull_model("tiny", lambda *event: events.append(event))
        self.assertEqual(events[1], ("pulling abc", 5, 10))
        self.assertEqual(events[-1], ("success", 0, 0))

    def test_cancelled_control_raises(self):
        _FakeOllama.replies = [(200, [{"response": "x"}, {"done": True}])]
        control = JobControl()
        control.cancel()
        with self.assertRaises(JobCancelled):
            self.generator._generate("t", "s", "m", 4096, False, control)

    def test_unreachable_server(self):
        generator = NoteGenerator(host="http://127.0.0.1:9")
        with self.assertRaisesRegex(NoteGenerationError, "Cannot connect"):
            generator._generate("t", "s", "m", 4096, False, None)


if __name__ == "__main__":
    unittest.main()
