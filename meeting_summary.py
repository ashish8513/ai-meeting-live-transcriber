import argparse
import json
import os
from pathlib import Path
import time
import torch

def load_transcripts(path: str):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if obj.get("type") == "transcript":
                    items.append(obj)
            except Exception:
                pass
    return items


def build_summarizer(prefer: str):
    client = None
    local = None
    if prefer in ("openai", "auto"):
        try:
            from openai import OpenAI
            client = OpenAI()
        except Exception:
            client = None
    if client is None and prefer in ("bart", "auto"):
        try:
            from transformers import pipeline
            local = pipeline("summarization", model="facebook/bart-large-cnn", device=0 if torch.cuda.is_available() else -1)
        except Exception:
            local = None
    return client, local


def summarize_text(client, local, text: str, model: str):
    text = text[-12000:]
    if client is not None:
        try:
            prompt = (
                "Summarize the following meeting transcript and return sections: Meeting Summary, Decisions & Action Items, Next Steps.\n\n" + text
            )
            resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.2)
            return resp.choices[0].message.content
        except Exception:
            pass
    if local is not None:
        try:
            out = local(text, max_length=300, min_length=120, do_sample=False)
            return out[0]["summary_text"]
        except Exception:
            pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default=None)
    ap.add_argument("--prefer", type=str, default="auto")
    ap.add_argument("--model", type=str, default=os.getenv("SUMMARY_MODEL", "gpt-4o-mini"))
    args = ap.parse_args()
    transcripts_dir = Path("transcripts")
    path = args.input
    if path is None:
        files = sorted(transcripts_dir.glob("session_*.jsonl"))
        if not files:
            print("No transcripts found.")
            return
        path = str(files[-1])
    items = load_transcripts(path)
    if not items:
        print("No transcript items.")
        return
    text = "\n".join([f"[{it['timestamp']}] ({it['speaker']}) {it['text']}" for it in items])
    client, local = build_summarizer(args.prefer)
    summary = summarize_text(client, local, text, args.model)
    out_md = Path(path).with_suffix("")
    out_md = str(out_md) + "_final_summary.md"
    if summary is None:
        print("Summarization unavailable.")
        return
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# Final Meeting Summary\n\n")
        f.write(summary)
    print("Wrote:", out_md)


if __name__ == "__main__":
    main()




