"""Feedback-service database setup."""

from __future__ import annotations

import os

from kanshan_shared.database import Base, get_engine, get_session_factory

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://kanshan:kanshan_dev_password@127.0.0.1:5432/kanshan",
)

_engine = None
_session_factory = None


def get_db_engine():
    global _engine
    if _engine is None:
        _engine = get_engine(DATABASE_URL)
    return _engine


def get_db_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = get_session_factory(get_db_engine())
    return _session_factory


def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(get_db_engine())
