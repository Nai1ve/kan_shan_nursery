"""SQLAlchemy models for feedback-service."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func

from kanshan_shared.database import Base


class FeedbackArticleTable(Base):
    __tablename__ = "articles"
    __table_args__ = {"schema": "feedback"}

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    title = Column(String, nullable=True)
    interest_id = Column(String, nullable=True)
    status = Column(String, nullable=True)
    data = Column(Text, nullable=False)  # Full article as JSON
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FeedbackSnapshotTable(Base):
    __tablename__ = "snapshots"
    __table_args__ = {"schema": "feedback"}

    id = Column(String, primary_key=True)
    article_id = Column(String, ForeignKey("feedback.articles.id"), nullable=False)
    captured_at = Column(DateTime, server_default=func.now())
    metrics_json = Column(Text, nullable=False)  # FeedbackMetrics as JSON
    comments_json = Column(Text, nullable=False)  # FeedbackComment[] as JSON


class FeedbackAnalysisTable(Base):
    __tablename__ = "analyses"
    __table_args__ = {"schema": "feedback"}

    id = Column(String, primary_key=True)
    article_id = Column(String, ForeignKey("feedback.articles.id"), nullable=False, unique=True)
    generated_at = Column(DateTime, server_default=func.now())
    data = Column(Text, nullable=False)  # FeedbackAnalysis as JSON
