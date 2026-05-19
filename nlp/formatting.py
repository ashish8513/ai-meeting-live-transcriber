"""Utilities for formatting transcript segments for display.

This keeps formatting logic in one place so both the backend and
any future tools can reuse the same conventions.
"""

from __future__ import annotations

from typing import Optional


def format_segment(speaker: Optional[str], text: str, timestamp: Optional[str]) -> str:
    """Format a single transcript segment.

    Example output (Zoom-like):
        [12:34:56] Speaker 1:
        Hello, how are you?
    """

    spk = (speaker or "Speaker").strip() or "Speaker"
    ts = (timestamp or "").strip()
    body = (text or "").strip()

    if ts:
        header = f"[{ts}] {spk}:"
    else:
        header = f"{spk}:"

    if not body:
        return header + "\n"

    return f"{header}\n{body}\n"
