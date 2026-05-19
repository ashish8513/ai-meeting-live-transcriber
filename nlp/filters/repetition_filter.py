from typing import Mapping, Optional


def _longest_overlap_suffix_prefix(a: str, b: str, min_chars: int) -> int:
    max_len = min(len(a), len(b))
    for length in range(max_len, min_chars - 1, -1):
        if a[-length:].lower() == b[:length].lower():
            return length
    return 0


def remove_overlap(
    prev_final_text: str,
    current_text: str,
    config: Optional[Mapping[str, object]] = None,
) -> str:
    """Merge previous final text and current interim, removing overlap.

    Example:
        prev = "My name is Rishi."
        current = "is Rishi from Bangalore"
        -> "My name is Rishi from Bangalore"

    This function is intentionally simple and deterministic so it can be
    used on every interim update without adding latency.
    """
    prev = (prev_final_text or "").strip()
    cur = (current_text or "").strip()

    if not prev and not cur:
        return ""
    if not prev:
        return cur
    if not cur:
        return prev

    min_overlap = 4
    if isinstance(config, Mapping):
        value = config.get("min_overlap_chars")
        if isinstance(value, int):
            min_overlap = max(1, int(value))

    overlap = _longest_overlap_suffix_prefix(prev, cur, min_overlap)
    if overlap <= 0:
        # No meaningful overlap: trust the current hypothesis as-is.
        return cur

    suffix = cur[overlap:]
    if suffix and prev and not prev.endswith(" ") and not suffix.startswith(" "):
        combined = f"{prev} {suffix}"
    else:
        combined = prev + suffix

    # Heuristic: if the raw current text is longer than the merged version,
    # keep the longer version.
    if len(cur) > len(combined):
        combined = cur

    return combined.strip()
