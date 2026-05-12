"""SQLAlchemy models for profile-service."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Text, func

from kanshan_shared.database import Base


class UserTable(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "profile"}

    user_id = Column(String, primary_key=True)
    nickname = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    username = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class SessionTable(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "profile"}

    session_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    expires_at = Column(String, nullable=True)


class ZhihuBindingTable(Base):
    __tablename__ = "zhihu_bindings"
    __table_args__ = {"schema": "profile"}

    user_id = Column(String, primary_key=True)
    zhihu_uid = Column(String, nullable=True)
    access_token = Column(Text, nullable=True)
    binding_status = Column(String, nullable=False, default="not_started")
    bound_at = Column(String, nullable=True)
    expired_at = Column(String, nullable=True)


class ProfileDataTable(Base):
    __tablename__ = "profile_data"
    __table_args__ = {"schema": "profile"}

    id = Column(String, primary_key=True, default="default")
    data = Column(Text, nullable=False)  # JSON string
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ProfileVersionTable(Base):
    __tablename__ = "profile_versions"
    __table_args__ = {"schema": "profile"}

    id = Column(String, primary_key=True)
    target = Column(String, nullable=False)
    snapshot = Column(Text, nullable=False)  # JSON string
    reason = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class MemoryUpdateRequestTable(Base):
    __tablename__ = "memory_update_requests"
    __table_args__ = {"schema": "profile"}

    id = Column(String, primary_key=True)
    interest_id = Column(String, nullable=False)
    target_field = Column(String, nullable=False)
    suggested_value = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(String, nullable=False)
