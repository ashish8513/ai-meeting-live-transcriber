from __future__ import annotations

from functools import lru_cache
from typing import Dict

from transformers import MarianMTModel, MarianTokenizer


class Translator:
    """Small wrapper around MarianMT for low-latency sentence translation.

    Instances are cheap to construct thanks to internal model caching.
    """

    def __init__(self, src: str = "en", tgt: str = "hi") -> None:
        model_name = f"Helsinki-NLP/opus-mt-{src}-{tgt}"
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name)

    def translate(self, text: str) -> str:
        if not text:
            return ""
        batch = self.tokenizer([text], return_tensors="pt", padding=True, truncation=True)
        gen = self.model.generate(**batch, max_length=200)
        return self.tokenizer.decode(gen[0], skip_special_tokens=True)


@lru_cache(maxsize=32)
def get_translator(src: str, tgt: str) -> Translator:
    """Return a cached Translator instance for the given language pair."""

    src_norm = (src or "en").lower()
    tgt_norm = (tgt or "en").lower()
    return Translator(src_norm, tgt_norm)
