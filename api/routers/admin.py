from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.deps import require_admin
from api.models import MeetingSession, RollingSummary, User
from api.schemas import AdminAnalytics, AdminDashboard, ChartBar, SessionAnalytics, SessionOut, SummaryOut

router = APIRouter(prefix="/admin", tags=["admin"])


def _summary_out(db: Session, row: RollingSummary) -> SummaryOut:
    session = db.query(MeetingSession).filter(MeetingSession.id == row.session_id).first()
    return SummaryOut(
        id=row.id,
        session_key=session.session_key if session else "",
        session_title=session.title if session else "",
        timestamp_label=row.timestamp_label,
        text=row.text,
        interval_seconds=row.interval_seconds,
        created_at=row.created_at,
    )


@router.get("/dashboard", response_model=AdminDashboard)
def dashboard(
    limit: int = Query(30, ge=1, le=200),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    active = db.query(MeetingSession).filter(MeetingSession.is_active.is_(True)).count()
    total = db.query(RollingSummary).count()
    rows = (
        db.query(RollingSummary)
        .order_by(RollingSummary.created_at.desc())
        .limit(limit)
        .all()
    )
    return AdminDashboard(
        active_sessions=active,
        total_summaries=total,
        latest_summaries=[_summary_out(db, r) for r in rows],
    )


@router.get("/summaries", response_model=list[SummaryOut])
def list_summaries(
    limit: int = Query(50, ge=1, le=500),
    session_key: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(RollingSummary).order_by(RollingSummary.created_at.desc())
    if session_key:
        session = db.query(MeetingSession).filter(MeetingSession.session_key == session_key).first()
        if session:
            q = q.filter(RollingSummary.session_id == session.id)
    rows = q.limit(limit).all()
    return [_summary_out(db, r) for r in rows]


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.query(MeetingSession).order_by(MeetingSession.started_at.desc()).limit(100).all()
    out = []
    for s in rows:
        cnt = db.query(func.count(RollingSummary.id)).filter(RollingSummary.session_id == s.id).scalar()
        out.append(
            SessionOut(
                id=s.id,
                session_key=s.session_key,
                title=s.title,
                is_active=s.is_active,
                started_at=s.started_at,
                summary_count=int(cnt or 0),
            )
        )
    return out


@router.get("/analytics", response_model=AdminAnalytics)
def analytics(
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sessions = db.query(MeetingSession).order_by(MeetingSession.started_at.desc()).limit(100).all()
    session_rows: list[SessionAnalytics] = []
    chart_bars: list[ChartBar] = []

    for s in sessions:
        cnt = int(
            db.query(func.count(RollingSummary.id)).filter(RollingSummary.session_id == s.id).scalar() or 0
        )
        latest = (
            db.query(RollingSummary)
            .filter(RollingSummary.session_id == s.id)
            .order_by(RollingSummary.created_at.desc())
            .first()
        )
        session_rows.append(
            SessionAnalytics(
                id=s.id,
                session_key=s.session_key,
                title=s.title,
                is_active=s.is_active,
                started_at=s.started_at,
                summary_count=cnt,
                latest_summary=(latest.text if latest else "")[:500],
                latest_at=latest.created_at if latest else None,
            )
        )
        label = s.session_key[-12:] if len(s.session_key) > 12 else s.session_key
        chart_bars.append(ChartBar(label=label, value=cnt))

    chart_bars.sort(key=lambda x: x.value, reverse=True)
    chart_bars = chart_bars[:12]

    latest = (
        db.query(RollingSummary).order_by(RollingSummary.created_at.desc()).limit(limit).all()
    )

    return AdminAnalytics(
        active_sessions=db.query(MeetingSession).filter(MeetingSession.is_active.is_(True)).count(),
        total_sessions=len(sessions),
        total_summaries=db.query(RollingSummary).count(),
        sessions=session_rows,
        chart_by_session=chart_bars,
        latest_summaries=[_summary_out(db, r) for r in latest],
    )
