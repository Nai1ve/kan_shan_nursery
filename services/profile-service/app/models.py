"""SQLAlchemy models for profile-service."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, func

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
    setup_state = Column(String, nullable=False, default="zhihu_pending")


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


class WritingStyleTable(Base):
    __tablename__ = "writing_styles"
    __table_args__ = {"schema": "profile"}

    user_id = Column(String, primary_key=True)
    logic_depth = Column(Integer, default=3)
    stance_sharpness = Column(Integer, default=3)
    personal_experience = Column(Integer, default=3)
    expression_sharpness = Column(Integer, default=3)
    uncertainty_tolerance = Column(Integer, default=3)
    preferred_format = Column(String, default="long_article")
    evidence_vs_judgment = Column(String, default="balanced")
    opening_style = Column(String, default="question")
    title_style = Column(String, default="controversy")
    emotional_temperature = Column(String, default="rational")
    ai_assistance_boundary = Column(String, default="draft_only")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class LLMConfigTable(Base):
    __tablename__ = "llm_configs"
    __table_args__ = {"schema": "profile"}

    user_id = Column(String, primary_key=True)
    provider = Column(String, default="openai_compat")
    model = Column(String, default="gpt-5.5")
    base_url = Column(String)
    api_key = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
