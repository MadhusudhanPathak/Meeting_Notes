"""Meeting-note generation through a local Ollama server."""

from __future__ import annotations

import http.client
import json
import re
import socket
import urllib.parse
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Callable, Dict, Iterator, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from meeting_notes.core.chunking import estimate_tokens, round_up, split_text
from meeting_notes.core.control import JobCancelled, JobControl

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
OLLAMA_DOWNLOAD_URL = "https://ollama.ai"
MODELS_TIMEOUT_SECONDS = 10
# Reading a long transcript can take many minutes on a CPU before the first token arrives.
STREAM_TIMEOUT_SECONDS = 3600
NO_RESPONSE_TEXT = "No response from model."

FALLBACK_CONTEXT_TOKENS = 4096
MIN_CONTEXT_TOKENS = 4096
# Upper bound for the context window we request; larger windows need much more memory.
MAX_CONTEXT_TOKENS = 32768
RESPONSE_TOKENS = 4096
PROMPT_OVERHEAD_TOKENS = 256
MIN_INPUT_TOKENS = 1024
MAX_CONDENSE_ROUNDS = 3

PART_SYSTEM_PROMPT = (
    "You help write meeting notes for a long meeting whose transcript has been split into "
    "consecutive parts. From the part you are given, extract everything needed for complete "
    "meeting notes: topics discussed with key points and context, decisions and who made them, "
    "action items with owners and deadlines, open questions, risks, and important names, "
    "numbers, and dates. Keep timestamps when the transcript has them. Write concise bullet "
    "points in the language of the transcript, with no introduction or conclusion."
)
PART_PROMPT = "Part {index} of {total} of the meeting transcript:\n\n{text}"
CONDENSE_PROMPT = (
    "Part {index} of {total} of the notes extracted from a long meeting. Merge duplicates and "
    "condense them, keeping every decision, action item, owner, deadline, and key fact:\n\n{text}"
)
COMBINE_PROMPT = (
    "The meeting transcript was too long to read at once, so it was split into consecutive "
    "parts and the important content of each part was extracted below. Treat these extracts "
    "as the complete record of the meeting and write the meeting notes.\n\n{text}"
)

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)

StatusCallback = Optional[Callable[[str], None]]
FractionCallback = Optional[Callable[[float], None]]
PullCallback = Optional[Callable[[str, int, int], None]]


class NoteGenerationError(Exception):
    """Raised when Ollama cannot be reached or returns an unusable response."""


@dataclass(frozen=True)
class ModelInfo:
    """Capabilities of an Ollama model that affect how notes are requested."""

    context_length: int = FALLBACK_CONTEXT_TOKENS
    supports_thinking: bool = False


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
        payload = self._request_json("get", "/api/tags", "getting Ollama models")
        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise NoteGenerationError("Invalid response format from Ollama API")
        try:
            return [model["name"] for model in models]
        except (KeyError, TypeError) as exc:
            raise NoteGenerationError(f"Error parsing Ollama response: {exc}") from exc

    def get_model_info(self, model: str) -> ModelInfo:
        """
        Return the context length and thinking support of ``model``.

        Raises:
            NoteGenerationError: If Ollama is unreachable or does not know the model.
        """
        payload = self._request_json(
            "post", "/api/show", f"reading details of model '{model}'", json={"model": model}
        )
        if not isinstance(payload, dict):
            return ModelInfo()
        model_info = payload.get("model_info") or {}
        lengths = [
            value for key, value in model_info.items()
            if key.endswith(".context_length") and isinstance(value, int) and value > 0
        ]
        capabilities = payload.get("capabilities") or []
        return ModelInfo(
            context_length=lengths[0] if lengths else FALLBACK_CONTEXT_TOKENS,
            supports_thinking="thinking" in capabilities,
        )

    def generate_notes(
        self,
        transcript: str,
        system_prompt: str,
        model: str,
        control: Optional[JobControl] = None,
        on_status: StatusCallback = None,
        on_fraction: FractionCallback = None,
    ) -> str:
        """
        Generate meeting notes for ``transcript`` using ``model`` and ``system_prompt``.

        The request's context window is sized to the transcript. Transcripts that are
        too long for the model are summarised part by part and then combined, so no
        part of the meeting is silently dropped.

        Raises:
            NoteGenerationError: If a request fails or the response cannot be decoded.
            JobCancelled: If ``control`` is cancelled.
        """
        report = on_status or (lambda message: None)
        info = self.get_model_info(model)
        context_limit = min(info.context_length, MAX_CONTEXT_TOKENS)
        input_budget = context_limit - RESPONSE_TOKENS - PROMPT_OVERHEAD_TOKENS
        if input_budget - estimate_tokens(system_prompt) < MIN_INPUT_TOKENS:
            raise NoteGenerationError(
                f"The system prompt is too long for model '{model}' "
                f"(context window: {info.context_length} tokens)."
            )

        def generate(prompt: str, system: str, num_ctx: int) -> str:
            return self._generate(prompt, system, model, num_ctx, info.supports_thinking, control)

        transcript_tokens = estimate_tokens(transcript)
        needed = estimate_tokens(system_prompt) + transcript_tokens
        if needed <= input_budget:
            wanted = round_up(needed + RESPONSE_TOKENS + PROMPT_OVERHEAD_TOKENS, 1024)
            num_ctx = min(context_limit, max(MIN_CONTEXT_TOKENS, wanted))
            report(
                f"Using a context window of {num_ctx} tokens "
                f"(transcript is about {transcript_tokens} tokens)."
            )
            notes = generate(transcript, system_prompt, num_ctx)
            _call(on_fraction, 1.0)
            return notes

        part_budget = (
            input_budget - estimate_tokens(PART_SYSTEM_PROMPT) - estimate_tokens(PART_PROMPT)
        )
        parts = split_text(transcript, part_budget)
        report(
            f"The transcript (about {transcript_tokens} tokens) is longer than model '{model}' "
            f"can read at once ({context_limit} tokens), so it will be summarised in "
            f"{len(parts)} parts first."
        )
        total_steps = len(parts) + 1
        extracts = []
        for index, part in enumerate(parts, start=1):
            report(f"Summarising part {index} of {len(parts)}...")
            prompt = PART_PROMPT.format(index=index, total=len(parts), text=part)
            extracts.append(generate(prompt, PART_SYSTEM_PROMPT, context_limit))
            _call(on_fraction, index / total_steps)

        combined = "\n\n".join(extracts)
        combine_budget = (
            input_budget - estimate_tokens(system_prompt) - estimate_tokens(COMBINE_PROMPT)
        )
        for _ in range(MAX_CONDENSE_ROUNDS):
            if estimate_tokens(combined) <= combine_budget:
                break
            pieces = split_text(combined, part_budget)
            report(f"Condensing the part summaries ({len(pieces)} groups)...")
            combined = "\n\n".join(
                generate(
                    CONDENSE_PROMPT.format(index=index, total=len(pieces), text=piece),
                    PART_SYSTEM_PROMPT,
                    context_limit,
                )
                for index, piece in enumerate(pieces, start=1)
            )

        report("Writing the final notes from the part summaries...")
        notes = generate(COMBINE_PROMPT.format(text=combined), system_prompt, context_limit)
        _call(on_fraction, 1.0)
        return notes

    def pull_model(
        self, model: str, on_progress: PullCallback = None, control: Optional[JobControl] = None
    ) -> None:
        """
        Download ``model`` into Ollama, reporting ``(status, completed, total)``.

        Raises:
            NoteGenerationError: If the download fails.
            JobCancelled: If ``control`` is cancelled.
        """
        for event in self._stream("/api/pull", {"model": model, "stream": True}, control):
            completed, total = event.get("completed"), event.get("total")
            _call(
                on_progress,
                str(event.get("status", "")),
                completed if isinstance(completed, int) else 0,
                total if isinstance(total, int) else 0,
            )

    def _generate(
        self,
        prompt: str,
        system: str,
        model: str,
        num_ctx: int,
        disable_thinking: bool,
        control: Optional[JobControl],
    ) -> str:
        payload: Dict[str, object] = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": True,
            "options": {"num_ctx": num_ctx},
        }
        if disable_thinking:
            payload["think"] = False
        pieces = []
        for event in self._stream("/api/generate", payload, control):
            piece = event.get("response")
            if isinstance(piece, str):
                pieces.append(piece)
            if event.get("done"):
                break
        text = _THINK_BLOCK.sub("", "".join(pieces)).strip()
        return text or NO_RESPONSE_TEXT

    def _request_json(self, method: str, path: str, action: str, **kwargs: object) -> object:
        try:
            response = self._session.request(
                method, f"{self.host}{path}", timeout=MODELS_TIMEOUT_SECONDS, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as exc:
            raise NoteGenerationError(
                "Cannot connect to Ollama. Please ensure Ollama is installed and running "
                f"(run 'ollama serve' in terminal). Visit {OLLAMA_DOWNLOAD_URL} to download "
                "and install Ollama."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise NoteGenerationError(f"HTTP error from Ollama API while {action}: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise NoteGenerationError(f"Request error while {action}: {exc}") from exc
        except ValueError as exc:
            raise NoteGenerationError(f"Error parsing Ollama response: {exc}") from exc

    def _stream(
        self, path: str, payload: Dict[str, object], control: Optional[JobControl]
    ) -> Iterator[dict]:
        """
        POST ``payload`` and yield each JSON line of the streamed reply.

        Uses a raw connection so that cancelling can close the socket immediately,
        even while Ollama is still reading the prompt.
        """
        url = urllib.parse.urlsplit(self.host)
        connection_class = (
            http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
        )
        connection = connection_class(
            url.hostname or "localhost", url.port, timeout=STREAM_TIMEOUT_SECONDS
        )

        def abort() -> None:
            if connection.sock is not None:
                try:
                    connection.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

        try:
            connection.connect()
            with (control.attach(abort=abort) if control else nullcontext()):
                connection.request(
                    "POST", url.path.rstrip("/") + path, body=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                response = connection.getresponse()
                if response.status >= 400:
                    raise NoteGenerationError(
                        f"Ollama returned HTTP {response.status}: {_error_message(response.read())}"
                    )
                for raw_line in response:
                    if control is not None:
                        control.checkpoint()
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise NoteGenerationError(f"Error decoding Ollama response: {exc}") from exc
                    if not isinstance(event, dict):
                        raise NoteGenerationError("Invalid response format from Ollama API")
                    if event.get("error"):
                        raise NoteGenerationError(f"Ollama error: {event['error']}")
                    yield event
        except (OSError, http.client.HTTPException) as exc:
            if control is not None and control.is_cancelled:
                raise JobCancelled() from exc
            if isinstance(exc, socket.timeout):
                raise NoteGenerationError("Request to Ollama timed out.") from exc
            raise NoteGenerationError(f"Cannot connect to Ollama. Is it running? ({exc})") from exc
        finally:
            connection.close()


def _call(callback: Optional[Callable[..., None]], *args: object) -> None:
    if callback is not None:
        callback(*args)


def _error_message(body: bytes) -> str:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return body.decode("utf-8", errors="replace")[:300] or "no details"
    if isinstance(payload, dict) and payload.get("error"):
        return str(payload["error"])
    return str(payload)[:300]
