from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(default="", max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    full_name: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class SummaryIngest(BaseModel):
    session_key: str
    timestamp: str = ""
    text: str
    interval_seconds: int = 5
    title: str = "Live Meeting"


class SummaryOut(BaseModel):
    id: int
    session_key: str
    session_title: str
    timestamp_label: str
    text: str
    interval_seconds: int
    created_at: datetime

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: int
    session_key: str
    title: str
    is_active: bool
    started_at: datetime
    summary_count: int = 0

    class Config:
        from_attributes = True


class AdminDashboard(BaseModel):
    active_sessions: int
    total_summaries: int
    latest_summaries: list[SummaryOut]


class SessionAnalytics(BaseModel):
    id: int
    session_key: str
    title: str
    is_active: bool
    started_at: datetime
    summary_count: int
    latest_summary: str = ""
    latest_at: Optional[datetime] = None


class ChartBar(BaseModel):
    label: str
    value: int


class AdminAnalytics(BaseModel):
    active_sessions: int
    total_sessions: int
    total_summaries: int
    sessions: list[SessionAnalytics]
    chart_by_session: list[ChartBar]
    latest_summaries: list[SummaryOut]
