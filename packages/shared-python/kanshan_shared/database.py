"""Shared database engine and session factory for PostgreSQL.

Usage::

    from kanshan_shared.database import get_engine, get_session_factory, Base

    engine = get_engine(database_url)
    SessionLocal = get_session_factory(engine)
    Base.metadata.create_all(engine)
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True, echo=False)


def get_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
