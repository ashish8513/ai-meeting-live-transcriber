import re
from typing import Iterable, Optional, Pattern, List


_DEFAULT_PATTERNS = [
    r"\((?:noise|noises|music|applause|laugh(?:ter)?)\)",
    r"\[(?:noise|noises|music|applause|laughter)\]",
    r"\[[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?(?:\.[0-9]{1,3})?\]",
]

_COMPILED: Pattern[str] | None = None


def _compile(patterns: Optional[Iterable[str]]) -> Pattern[str]:
    """Compile noise regex from config, falling back to safe defaults."""
    global _COMPILED
    if _COMPILED is not None:
        return _COMPILED

    pats: List[str] = [p for p in (patterns or []) if p]
    if not pats:
        pats = _DEFAULT_PATTERNS

    combined = "|".join(f"(?:{p})" for p in pats)
    _COMPILED = re.compile(combined, flags=re.IGNORECASE)
    return _COMPILED


def clean_noise(text: str, custom_patterns: Optional[Iterable[str]] = None) -> str:
    """Remove noise annotations like (noise), [applause], timestamps, etc.

    Pure regex-based; intended to be ~O(n) and zero-allocation aside from
    the returned string.
    """
    if not text:
        return ""

    pattern = _compile(custom_patterns)
    cleaned = pattern.sub(" ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
