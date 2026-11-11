"""Token estimates and splitting of long text so it fits a model's context window."""

from __future__ import annotations

from typing import List

# Most tokenizers use roughly 3-4 characters per token for Latin script and about
# one token per character (or more) for other scripts, so err on the high side.
_CHARS_PER_ASCII_TOKEN = 3


def estimate_tokens(text: str) -> int:
    """Return a deliberately generous estimate of the token count of ``text``."""
    ascii_chars = sum(1 for char in text if ord(char) < 128)
    other_chars = len(text) - ascii_chars
    return ascii_chars // _CHARS_PER_ASCII_TOKEN + other_chars + 1


def round_up(value: int, multiple: int) -> int:
    return -(-value // multiple) * multiple


def split_text(text: str, max_tokens: int) -> List[str]:
    """
    Split ``text`` into consecutive chunks of at most ``max_tokens`` (estimated).

    Splits happen at line breaks; a single line that is too long is split at spaces,
    and a single word that is too long is split by characters.
    """
    if max_tokens < 1:
        raise ValueError("max_tokens must be positive")

    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0
    for piece in _pieces(text, max_tokens):
        piece_tokens = estimate_tokens(piece)
        if current and current_tokens + piece_tokens > max_tokens:
            chunks.append("\n".join(current))
            current, current_tokens = [], 0
        current.append(piece)
        current_tokens += piece_tokens
    if current:
        chunks.append("\n".join(current))
    return [chunk for chunk in chunks if chunk.strip()]


def _pieces(text: str, max_tokens: int) -> List[str]:
    pieces: List[str] = []
    for line in text.splitlines():
        if estimate_tokens(line) <= max_tokens:
            pieces.append(line)
            continue
        words: List[str] = []
        for word in line.split(" "):
            candidate = " ".join(words + [word])
            if words and estimate_tokens(candidate) > max_tokens:
                pieces.append(" ".join(words))
                words = []
            if estimate_tokens(word) > max_tokens:
                pieces.extend(_split_word(word, max_tokens))
            else:
                words.append(word)
        if words:
            pieces.append(" ".join(words))
    return pieces


def _split_word(word: str, max_tokens: int) -> List[str]:
    parts: List[str] = []
    current = ""
    for char in word:
        if current and estimate_tokens(current + char) > max_tokens:
            parts.append(current)
            current = ""
        current += char
    if current:
        parts.append(current)
    return parts
