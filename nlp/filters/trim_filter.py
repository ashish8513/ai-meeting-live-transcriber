from typing import Mapping, Optional, Set


_COMMON_SHORT_WORDS: Set[str] = {
    "a",
    "i",
    "an",
    "am",
    "as",
    "at",
    "be",
    "by",
    "do",
    "go",
    "he",
    "if",
    "in",
    "is",
    "it",
    "me",
    "my",
    "no",
    "of",
    "on",
    "or",
    "so",
    "to",
    "up",
    "us",
    "we",
    "you",
    "and",
    "are",
    "but",
    "for",
    "not",
    "the",
    "this",
    "that",
    "with",
    "from",
    "have",
    "just",
    "like",
    "will",
}


def trim_incomplete(
    text: str,
    config: Optional[Mapping[str, object]] = None,
    *,
    is_final: bool = False,
) -> str:
    """Trim a likely half-spoken trailing word from interim chunks.

    Heuristic: if the last token is short, alphabetic, and not a very common
    English short word, drop it for interim output. Finalized chunks are
    returned unchanged.
    """
    stripped = (text or "").rstrip()
    if not stripped:
        return ""

    if is_final:
        return stripped

    words = stripped.split()
    if not words:
        return ""

    last = words[-1]

    min_len = 2
    if isinstance(config, Mapping):
        value = config.get("min_word_length")
        if isinstance(value, int):
            min_len = max(1, int(value))

    candidate = last.strip()
    if not candidate.isalpha():
        return stripped

    lower = candidate.lower()

    if (len(candidate) <= min_len and lower not in _COMMON_SHORT_WORDS) or (
        len(candidate) <= 4 and lower not in _COMMON_SHORT_WORDS
    ):
        words = words[:-1]

    return " ".join(words).strip()
