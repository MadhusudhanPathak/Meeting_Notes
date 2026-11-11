"""Meeting-note generation through a local Ollama server."""

from __future__ import annotations

import json
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
OLLAMA_DOWNLOAD_URL = "https://ollama.ai"
MODELS_TIMEOUT_SECONDS = 10
GENERATE_TIMEOUT_SECONDS = 300
NO_RESPONSE_TEXT = "No response from model."


class NoteGenerationError(Exception):
    """Raised when Ollama cannot be reached or returns an unusable response."""


def _create_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(
        max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class NoteGenerator:
    """Client for the Ollama HTTP API."""

    def __init__(
        self, host: str = DEFAULT_OLLAMA_HOST, session: Optional[requests.Session] = None
    ) -> None:
        self.host = host.rstrip("/")
        self._session = session or _create_session()

    def get_available_models(self) -> List[str]:
        """
        Return the names of the models installed in Ollama.

        Raises:
            NoteGenerationError: If Ollama is unreachable or the response is malformed.
        """
        try:
            response = self._session.get(f"{self.host}/api/tags", timeout=MODELS_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.ConnectionError as exc:
            raise NoteGenerationError(
                "Cannot connect to Ollama. Please ensure Ollama is installed and running "
                f"(run 'ollama serve' in terminal). Visit {OLLAMA_DOWNLOAD_URL} to download "
                "and install Ollama."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise NoteGenerationError(f"HTTP error from Ollama API: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise NoteGenerationError(f"Request error when getting Ollama models: {exc}") from exc
        except ValueError as exc:
            raise NoteGenerationError(f"Error parsing Ollama response: {exc}") from exc

        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise NoteGenerationError("Invalid response format from Ollama API")
        try:
            return [model["name"] for model in models]
        except (KeyError, TypeError) as exc:
            raise NoteGenerationError(f"Error parsing Ollama response: {exc}") from exc

    def generate_notes(self, transcript: str, system_prompt: str, model: str) -> str:
        """
        Generate meeting notes for ``transcript`` using ``model`` and ``system_prompt``.

        Raises:
            NoteGenerationError: If the request fails or the response cannot be decoded.
        """
        payload = {"model": model, "prompt": transcript, "system": system_prompt, "stream": False}
        try:
            response = self._session.post(
                f"{self.host}/api/generate", json=payload, timeout=GENERATE_TIMEOUT_SECONDS
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise NoteGenerationError("Cannot connect to Ollama. Is it running?") from exc
        except requests.exceptions.Timeout as exc:
            raise NoteGenerationError(
                "Request to Ollama timed out. The processing might be taking too long."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise NoteGenerationError(f"HTTP error from Ollama API: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise NoteGenerationError(f"Request error during note generation: {exc}") from exc

        # A non-streaming reply is one JSON object; streamed replies end with the final object.
        lines = response.text.strip().splitlines()
        try:
            final = json.loads(lines[-1])
        except (IndexError, json.JSONDecodeError) as exc:
            raise NoteGenerationError(f"Error decoding Ollama response: {exc}") from exc

        if not isinstance(final, dict):
            raise NoteGenerationError("Invalid response format from Ollama API")
        notes = final.get("response")
        return notes if isinstance(notes, str) else NO_RESPONSE_TEXT
