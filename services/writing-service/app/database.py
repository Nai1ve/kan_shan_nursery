"""Writing-service database setup."""

from __future__ import annotations

from kanshan_shared import load_config
from kanshan_shared.database import Base, get_engine, get_session_factory

_config = load_config()
DATABASE_URL = _config.database_url

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
