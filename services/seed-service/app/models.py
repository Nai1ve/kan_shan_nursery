"""SQLAlchemy models for seed-service."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Text, func

from kanshan_shared.database import Base


class SeedTable(Base):
    __tablename__ = "seeds"
    __table_args__ = {"schema": "seed"}

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    interest_id = Column(String, nullable=True)
    core_claim = Column(Text, nullable=True)
    user_reaction = Column(String, nullable=True)
    status = Column(String, nullable=True)
    maturity_score = Column(String, nullable=True)
    data = Column(Text, nullable=False)  # Full seed as JSON
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
