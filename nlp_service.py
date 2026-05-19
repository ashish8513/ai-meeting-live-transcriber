"""FastAPI NLP microservice for transcript cleanup.

Used by realtime_transcriber when NLP_SERVICE_URL is set (default http://localhost:8100).
"""
import os
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from nlp.pipeline import process_interim_text

app = FastAPI(title="NLP Service", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CorrectRequest(BaseModel):
    text: str
    context: Optional[str] = None
    is_final: bool = True


class CorrectResponse(BaseModel):
    corrected_text: str


def _parse_history(context: str) -> List[str]:
    """Parse '(speaker) text' lines from meeting context."""
    lines: List[str] = []
    for raw in context.splitlines():
        line = raw.strip()
        if not line:
            continue
        if ")" in line and line.startswith("("):
            try:
                _, rest = line.split(")", 1)
                line = rest.strip()
            except ValueError:
                pass
        if line:
            lines.append(line)
    return lines


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "nlp"}


@app.post("/correct", response_model=CorrectResponse)
async def correct(req: CorrectRequest) -> CorrectResponse:
    text = (req.text or "").strip()
    if not text:
        return CorrectResponse(corrected_text="")

    ctx = (req.context or "").strip()
    history = _parse_history(ctx) if ctx else []
    prev_final = history[-1] if history else ""

    result = process_interim_text(
        text,
        prev_final,
        is_final=bool(req.is_final),
    )
    corrected = (result.get("text") or text).strip()
    return CorrectResponse(corrected_text=corrected)


@app.post("/interim", response_model=CorrectResponse)
async def interim(req: CorrectRequest) -> CorrectResponse:
    return await correct(
        CorrectRequest(text=req.text, context=req.context, is_final=False)
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("NLP_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("NLP_SERVICE_PORT", "8100"))
    uvicorn.run(app, host=host, port=port)
