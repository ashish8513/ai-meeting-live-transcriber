"""Legacy text cleaner — used by tests; NLP service uses nlp.pipeline."""
import re

_NOISE_PATTERNS = [
    r"\((?:uh+|um+|hmm+|erm+|ah+|noise|mic crack|crosstalk|static|silence)\)",
    r"\[(?:noise|music|laughter|applause|static|background)\]",
    r"<[^>]+>",
]

_FILLER_WORDS = {"uh", "uhh", "umm", "um", "hmm", "erm", "like"}


def _remove_noise_tokens(text: str) -> str:
    result = text
    for pattern in _NOISE_PATTERNS:
        result = re.sub(pattern, " ", result, flags=re.IGNORECASE)
    return result


def _remove_repeated_punctuation(text: str) -> str:
    return re.sub(r"[!?.,]{2,}", lambda m: m.group(0)[0], text)


def _remove_fillers(text: str) -> str:
    words = text.split()
    cleaned = []
    for w in words:
        if w.lower().strip(".,?!") in _FILLER_WORDS:
            continue
        cleaned.append(w)
    return " ".join(cleaned)


def clean_text(text: str) -> str:
    if not text:
        return ""
    s = text.strip()
    s = _remove_noise_tokens(s)
    s = _remove_fillers(s)
    s = _remove_repeated_punctuation(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()
