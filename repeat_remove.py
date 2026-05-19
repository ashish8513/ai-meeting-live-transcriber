"""Legacy repetition removal — NLP service uses nlp.pipeline."""
from difflib import SequenceMatcher
from typing import Iterable, Optional


def _longest_overlap_suffix_prefix(a: str, b: str) -> int:
    max_len = min(len(a), len(b))
    for length in range(max_len, 0, -1):
        if a[-length:].lower() == b[:length].lower():
            return length
    return 0


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def remove_repetitions(
    history: Iterable[str], current: str, threshold: float = 0.92
) -> str:
    text = (current or "").strip()
    if not text:
        return ""

    last: Optional[str] = None
    for item in history:
        candidate = (item or "").strip()
        if candidate:
            last = candidate
    if not last:
        return text

    if _similarity(last, text) >= threshold:
        return text if len(text) >= len(last) else last

    overlap = _longest_overlap_suffix_prefix(last, text)
    if overlap >= 4:
        text = last + text[overlap:]

    words = text.split()
    if not words:
        return ""
    dedup = [words[0]]
    for w in words[1:]:
        if w.lower() != dedup[-1].lower():
            dedup.append(w)
    return " ".join(dedup).strip()
