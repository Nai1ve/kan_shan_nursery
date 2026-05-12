"""SQLAlchemy models for writing-service."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Text, func

from kanshan_shared.database import Base


class WritingSessionTable(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "writing"}

    session_id = Column(String, primary_key=True)
    state = Column(String, nullable=False)
    data = Column(Text, nullable=False)  # Full session as JSON
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
