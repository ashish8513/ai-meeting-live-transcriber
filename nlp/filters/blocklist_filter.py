from typing import Iterable, List, Mapping, Optional


def _normalize_list(items: Optional[Iterable[str]]) -> List[List[str]]:
    phrases: List[List[str]] = []
    if not items:
        return phrases
    for raw in items:
        phrase = (raw or "").strip().lower()
        if not phrase:
            continue
        phrases.append(phrase.split())
    return phrases


def clean_blocklist(text: str, config: Optional[Mapping[str, object]] = None) -> str:
    """Remove simple hallucinated prefixes/suffixes (so, okay, yeah, thank you).

    Removals only happen at the string boundaries and are purely rule-based
    and case-insensitive.
    """
    if not text:
        return ""

    words = (text or "").strip().split()
    if not words:
        return ""

    prefixes: List[List[str]] = []
    suffixes: List[List[str]] = []

    if isinstance(config, Mapping):
        prefixes = _normalize_list(config.get("prefixes"))
        suffixes = _normalize_list(config.get("suffixes"))

    if not prefixes and not suffixes:
        prefixes = _normalize_list(["so", "okay", "ok", "yeah", "thank you", "thanks"])
        suffixes = _normalize_list(["okay", "yeah", "thank you", "thanks"])

    lowered = [w.lower() for w in words]

    while True:
        removed = False

        for p in prefixes:
            n = len(p)
            if n and len(lowered) >= n and lowered[:n] == p:
                words = words[n:]
                lowered = lowered[n:]
                removed = True
                break

        if not words or not lowered:
            break

        for s in suffixes:
            n = len(s)
            if n and len(lowered) >= n and lowered[-n:] == s:
                words = words[:-n]
                lowered = lowered[:-n]
                removed = True
                break

        if not removed or not words or not lowered:
            break

    if not words:
        return ""

    return " ".join(words).strip()
