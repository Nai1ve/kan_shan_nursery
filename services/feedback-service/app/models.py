"""SQLAlchemy models for feedback-service."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Text, func

from kanshan_shared.database import Base


class FeedbackArticleTable(Base):
    __tablename__ = "articles"
    __table_args__ = {"schema": "feedback"}

    id = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    interest_id = Column(String, nullable=True)
    status = Column(String, nullable=True)
    data = Column(Text, nullable=False)  # Full article as JSON
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
