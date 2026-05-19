# Streaming NLP Pipeline

Lightweight, rule-based NLP filters that run on every interim ASR update
without increasing latency. Designed for Whisper / RNNT streaming output
in this repo.

## Modules

- `nlp/pipeline.py`
- `nlp/filters/noise_filter.py`
- `nlp/filters/repetition_filter.py`
- `nlp/filters/blocklist_filter.py`
- `nlp/filters/trim_filter.py`
- `nlp/config/rules.json`

## Core API

```python
from nlp.pipeline import process_interim_text

result = process_interim_text(current_text, prev_final_text, is_final=False)
print(result["final"], result["text"])
```

- **`current_text`**: interim ASR chunk text
- **`prev_final_text`**: last *finalized* utterance text for this speaker
- **`is_final`**: whether this chunk is being finalized by the ASR backend

The function returns:

```json
{"final": bool, "text": "clean processed text"}
```

## Filters

- **Noise removal** (`noise_filter.clean_noise`)
  - Removes `(noise)`, `(laugh)`, `[applause]`, and simple timestamps via regex.
- **Repetition / overlap removal** (`repetition_filter.remove_overlap`)
  - Merges `prev_final_text` and `current_text`, dropping overlapping prefix
    in `current_text` and keeping the longer version when uncertain.
- **Blocklist hallucination filter** (`blocklist_filter.clean_blocklist`)
  - Strips simple fillers / outros like `so`, `okay`, `yeah`, `thank you`,
    but **only** when they appear at the start or end of the string.
- **Trim incomplete word** (`trim_filter.trim_incomplete`)
  - For interim chunks, drops a likely half-spoken trailing word. Final
    chunks (`is_final=True`) are returned unchanged.

All filters are pure functions and run in O(n) on the input text.

## Configuration (`rules.json`)

- **`noise_patterns`**: list of regex strings (OR'ed together) used for
  noise/annotation removal.
- **`blocklist.prefixes` / `blocklist.suffixes`**: phrases to trim only at
  the start/end of the string.
- **`repetition.min_overlap_chars`**: minimum overlap size when joining
  `prev_final_text` and `current_text`.
- **`trim.min_word_length`**: lower bound for treating short trailing tokens
  as incomplete.

Edit `nlp/config/rules.json` and reload your backend to change behavior.

## Example integration with `realtime_transcriber.py`

1. **Import the pipeline** near the top of `realtime_transcriber.py`:

```python
from nlp.pipeline import process_interim_text
```

2. **When emitting interim text to the frontend**, wrap the ASR hypothesis
   through the pipeline. For example, around where `partial_payload` is
   built (variables may differ slightly in your local file):

```python
# before
text = whisper_transcribe_chunk(...)

# previous final text for this speaker (if any)
last_final = ""
last = last_sent_per_speaker.get(speaker_label)
if last:
    last_final = last[0]

res = process_interim_text(text, last_final, is_final=False)
clean_text = res["text"]

partial_payload = {
    "type": "interim",
    "stream_id": stream_id,
    "timestamp": ts_str,
    "speaker": speaker_label,
    "text": clean_text,
}
```

3. **When finalizing text in `pending_flusher`**, apply the same pipeline
   with `is_final=True` so the client receives fully cleaned text:

```python
res = process_interim_text(final_text, last_final_text_for_speaker, is_final=True)
final_clean = res["text"]
```

This keeps all ASR core logic (chunking, VAD, decoding) unchanged while
adding a low-latency, fully local NLP post-processing layer.
