"""Legacy finalizer — NLP service uses nlp.pipeline."""
import re

_BLOCKLIST = {
    "thank you",
    "thank you very much",
    "thanks",
    "thanks for watching",
    "so",
    "okay",
    "ok",
    "i don't know",
    "home",
    "i'll see you in the next video",
    "we'll see you next time",
    "bye",
}


def _is_hallucination(text: str) -> bool:
    t = (text or "").lower().strip()
    for ch in ".!,?":
        t = t.replace(ch, "")
    for phrase in _BLOCKLIST:
        if not phrase:
            continue
        if t == phrase or t.startswith(phrase + " "):
            return True
    return False


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _ensure_terminal_punctuation(text: str) -> str:
    if not text:
        return ""
    if text[-1] not in {".", "?", "!"}:
        return text + "."
    return text


def _capitalize_first_alpha(text: str) -> str:
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch.isalpha():
            chars[i] = ch.upper()
            break
    return "".join(chars)


def finalize_text(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    if _is_hallucination(s):
        return ""
    s = _normalize_spaces(s)
    s = _ensure_terminal_punctuation(s)
    s = _capitalize_first_alpha(s)
    return s
