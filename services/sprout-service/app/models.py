"""SQLAlchemy models for sprout-service."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Text, func

from kanshan_shared.database import Base


class SproutOpportunityTable(Base):
    __tablename__ = "opportunities"
    __table_args__ = {"schema": "sprout"}

    id = Column(String, primary_key=True)
    seed_id = Column(String, nullable=True)
    interest_id = Column(String, nullable=True)
    status = Column(String, nullable=True)
    score = Column(String, nullable=True)
    data = Column(Text, nullable=False)  # Full opportunity as JSON
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SproutRunTable(Base):
    __tablename__ = "runs"
    __table_args__ = {"schema": "sprout"}

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    interest_id = Column(String, nullable=True)
    status = Column(String, nullable=True)
    data = Column(Text, nullable=False)  # Full run as JSON
    created_at = Column(DateTime, server_default=func.now())
