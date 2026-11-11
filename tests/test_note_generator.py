import unittest
from unittest import mock

import requests

from meeting_notes.core.note_generator import NoteGenerationError, NoteGenerator


def _response(text="", json_data=None, status=200):
    response = mock.Mock()
    response.text = text
    response.json.return_value = json_data
    if status >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status} error")
    return response


class NoteGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.generator = NoteGenerator(session=self.session)

    def test_lists_model_names(self):
        self.session.get.return_value = _response(json_data={"models": [{"name": "llama2"}]})
        self.assertEqual(self.generator.get_available_models(), ["llama2"])

    def test_connection_failure_is_wrapped(self):
        self.session.get.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaisesRegex(NoteGenerationError, "Cannot connect to Ollama"):
            self.generator.get_available_models()

    def test_invalid_models_payload(self):
        self.session.get.return_value = _response(json_data=["unexpected"])
        with self.assertRaises(NoteGenerationError):
            self.generator.get_available_models()

    def test_generate_returns_final_response(self):
        self.session.post.return_value = _response(text='{"response": "notes"}\n')
        self.assertEqual(self.generator.generate_notes("t", "s", "m"), "notes")

    def test_generate_without_response_field(self):
        self.session.post.return_value = _response(text="{}")
        self.assertEqual(self.generator.generate_notes("t", "s", "m"), "No response from model.")

    def test_generate_empty_body_raises(self):
        self.session.post.return_value = _response(text="")
        with self.assertRaises(NoteGenerationError):
            self.generator.generate_notes("t", "s", "m")

    def test_generate_http_error_raises(self):
        self.session.post.return_value = _response(status=404)
        with self.assertRaisesRegex(NoteGenerationError, "HTTP error"):
            self.generator.generate_notes("t", "s", "m")


if __name__ == "__main__":
    unittest.main()
