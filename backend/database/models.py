"""
SQLAlchemy ORM models for incident storage.
Supports both SQLite (default / dev) and PostgreSQL (prod).
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session

from backend.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class IncidentModel(Base):
    __tablename__ = "incidents"

    incident_id           = Column(String, primary_key=True, index=True)
    timestamp             = Column(DateTime, default=datetime.utcnow, index=True)
    severity              = Column(String, nullable=False)
    severity_confidence   = Column(Float, default=0.0)
    anomaly               = Column(Boolean, default=False)
    anomaly_score         = Column(Float, default=0.0)
    root_cause            = Column(String, nullable=False)
    root_cause_confidence = Column(Float, default=0.0)
    tower                 = Column(String, default="")
    service               = Column(String, default="")
    cpu_usage             = Column(Float, default=0.0)
    memory_usage          = Column(Float, default=0.0)
    disk_usage            = Column(Float, default=0.0)
    error_count           = Column(Integer, default=0)
    latency_ms            = Column(Float, default=0.0)
    report_json           = Column(Text, default="{}")     # serialised JSON report
    report_markdown       = Column(Text, default="")
    similar_incident_ids  = Column(Text, default="")       # comma-separated

    def __repr__(self):
        return f"<Incident {self.incident_id} | {self.severity} | {self.root_cause}>"


# ── Engine / session factory ──────────────────────────────────────

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        _engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
        Base.metadata.create_all(_engine)
    return _engine


def get_session() -> Session:
    return Session(get_engine())
