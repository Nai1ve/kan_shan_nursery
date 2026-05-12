from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import bcrypt


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class User:
    def __init__(
        self,
        user_id: str,
        nickname: str,
        email: str | None,
        username: str | None,
        password_hash: str,
        created_at: str,
    ) -> None:
        self.user_id = user_id
        self.nickname = nickname
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "userId": self.user_id,
            "nickname": self.nickname,
            "email": self.email,
            "username": self.username,
            "createdAt": self.created_at,
        }


class UserSession:
    def __init__(self, session_id: str, user_id: str, created_at: str, expires_at: str) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = created_at
        self.expires_at = expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessionId": self.session_id,
            "userId": self.user_id,
            "createdAt": self.created_at,
            "expiresAt": self.expires_at,
        }


class ZhihuBinding:
    def __init__(
        self,
        user_id: str,
        zhihu_uid: str | None,
        access_token: str | None,
        binding_status: str,
        bound_at: str | None,
        expired_at: str | None,
    ) -> None:
        self.user_id = user_id
        self.zhihu_uid = zhihu_uid
        self.access_token = access_token
        self.binding_status = binding_status
        self.bound_at = bound_at
        self.expired_at = expired_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "userId": self.user_id,
            "zhihuUid": self.zhihu_uid,
            "bindingStatus": self.binding_status,
            "boundAt": self.bound_at,
            "expiredAt": self.expired_at,
        }


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))