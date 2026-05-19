import json
import logging
from pathlib import Path
from typing import Any, Dict

from .filters.noise_filter import clean_noise
from .filters.repetition_filter import remove_overlap
from .filters.blocklist_filter import clean_blocklist
from .filters.trim_filter import trim_incomplete


logger = logging.getLogger(__name__)

_RULES_CACHE: Dict[str, Any] | None = None


def load_rules() -> Dict[str, Any]:
    """Load NLP rules from config/rules.json (cached after first call)."""
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE

    cfg_path = Path(__file__).resolve().parent / "config" / "rules.json"
    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            _RULES_CACHE = json.load(f)
    except FileNotFoundError:
        logger.warning("NLP rules.json not found at %s, using built-in defaults", cfg_path)
        _RULES_CACHE = {}
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Failed to load NLP rules.json: %s", e)
        _RULES_CACHE = {}
    return _RULES_CACHE


def process_interim_text(current_text: str, prev_final_text: str, is_final: bool = False) -> Dict[str, Any]:
    """Clean streaming ASR text with a lightweight, rule-based pipeline.

    The function is designed to be called on every interim update.
    It is stateless apart from the provided ``prev_final_text``.

    Returns a dict compatible with your frontend contract:
        {"final": bool, "text": "clean processed text"}
    """
    rules = load_rules()

    text = current_text or ""
    prev_final = prev_final_text or ""

    if not text.strip() and not prev_final.strip():
        return {"final": bool(is_final), "text": ""}

    logger.debug(
        "NLP pipeline input | final=%s | prev='%s' | current='%s'",
        is_final,
        prev_final,
        text,
    )

    text = clean_noise(text, rules.get("noise_patterns"))
    text = remove_overlap(prev_final, text, rules.get("repetition"))
    text = clean_blocklist(text, rules.get("blocklist"))
    text = trim_incomplete(text, rules.get("trim"), is_final=is_final)

    logger.debug("NLP pipeline output | final=%s | text='%s'", is_final, text)
    return {"final": bool(is_final), "text": text}
