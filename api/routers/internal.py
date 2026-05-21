from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from api.config import get_settings
from api.database import get_db
from api.models import MeetingSession, RollingSummary
from api.schemas import SummaryIngest, SummaryOut

router = APIRouter(prefix="/internal", tags=["internal"])
settings = get_settings()


def verify_internal_key(x_internal_key: str | None = Header(default=None)):
    if not x_internal_key or x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=403, detail="Invalid internal API key")


@router.post("/summaries", response_model=SummaryOut)
def ingest_summary(
    body: SummaryIngest,
    _: None = Depends(verify_internal_key),
    db: Session = Depends(get_db),
):
    key = body.session_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="session_key required")
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")

    session = db.query(MeetingSession).filter(MeetingSession.session_key == key).first()
    if not session:
        session = MeetingSession(session_key=key, title=body.title or "Live Meeting", is_active=True)
        db.add(session)
        db.flush()
    else:
        session.is_active = True
        if body.title:
            session.title = body.title

    row = RollingSummary(
        session_id=session.id,
        timestamp_label=body.timestamp or "",
        text=text,
        interval_seconds=body.interval_seconds,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return SummaryOut(
        id=row.id,
        session_key=session.session_key,
        session_title=session.title,
        timestamp_label=row.timestamp_label,
        text=row.text,
        interval_seconds=row.interval_seconds,
        created_at=row.created_at,
    )
