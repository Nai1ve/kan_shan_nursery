from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .models import User, UserSession, ZhihuBinding, create_id, hash_password, now_iso, verify_password


class AuthError(Exception):
    pass


class AuthService:
    SESSION_TTL_HOURS = 24

    def __init__(self, repository: AuthRepository) -> None:
        self._repo = repository

    def register(self, nickname: str, password: str, email: str | None = None, username: str | None = None) -> dict[str, Any]:
        if not nickname:
            raise AuthError("nickname is required")
        if not password or len(password) < 6:
            raise AuthError("password must be at least 6 characters")

        if email and self._repo.get_user_by_email(email):
            raise AuthError("email already registered")
        if username and self._repo.get_user_by_username(username):
            raise AuthError("username already taken")

        user = User(
            user_id=create_id("user"),
            nickname=nickname,
            email=email,
            username=username,
            password_hash=hash_password(password),
            created_at=now_iso(),
        )
        self._repo.create_user(user)

        session = self._create_session(user.user_id)
        return {
            "user": user.to_dict(),
            "session": session.to_dict(),
            "setupState": "zhihu_pending",
        }

    def login(self, identifier: str, password: str) -> dict[str, Any]:
        user = self._get_user_by_identifier(identifier)
        if not user:
            raise AuthError("invalid credentials")
        if not verify_password(password, user.password_hash):
            raise AuthError("invalid credentials")

        session = self._create_session(user.user_id)
        setup_state = self._determine_setup_state(user.user_id)
        return {
            "user": user.to_dict(),
            "session": session.to_dict(),
            "setupState": setup_state,
        }

    def logout(self, session_id: str) -> dict[str, Any]:
        self._repo.delete_session(session_id)
        return {"success": True}

    def me(self, session_id: str | None) -> dict[str, Any]:
        if not session_id:
            return {"authenticated": False, "user": None, "setupState": None}

        session = self._repo.get_session(session_id)
        if not session:
            return {"authenticated": False, "user": None, "setupState": None}

        user = self._repo.get_user_by_id(session.user_id)
        if not user:
            return {"authenticated": False, "user": None, "setupState": None}

        setup_state = self._determine_setup_state(user.user_id)
        return {
            "authenticated": True,
            "user": user.to_dict(),
            "setupState": setup_state,
        }

    def get_zhihu_binding(self, user_id: str) -> dict[str, Any]:
        binding = self._repo.get_zhihu_binding(user_id)
        if not binding:
            return {
                "bindingStatus": "not_started",
                "userId": user_id,
                "zhihuUid": None,
                "boundAt": None,
                "expiredAt": None,
            }
        return binding.to_dict()

    def create_zhihu_binding(self, user_id: str, zhihu_uid: str, access_token: str, expires_in: int) -> dict[str, Any]:
        now = now_iso()
        expired_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat() if expires_in else None

        binding = ZhihuBinding(
            user_id=user_id,
            zhihu_uid=zhihu_uid,
            access_token=access_token,
            binding_status="bound",
            bound_at=now,
            expired_at=expired_at,
        )
        self._repo.save_zhihu_binding(binding)
        return binding.to_dict()

    def delete_zhihu_binding(self, user_id: str) -> dict[str, Any]:
        binding = self._repo.get_zhihu_binding(user_id)
        if binding:
            binding.binding_status = "skipped"
            self._repo.save_zhihu_binding(binding)
        return {"success": True}

    def get_zhihu_authorize_url(self) -> dict[str, Any]:
        return {"url": "https://www.zhihu.com/oauth/authorize?client_id=MOCK&redirect_uri=MOCK&response_type=code&scope=MOCK"}

    def _get_user_by_identifier(self, identifier: str) -> User | None:
        if "@" in identifier:
            return self._repo.get_user_by_email(identifier)
        return self._repo.get_user_by_username(identifier)

    def _create_session(self, user_id: str) -> UserSession:
        now = now_iso()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=self.SESSION_TTL_HOURS)).isoformat()
        session = UserSession(
            session_id=create_id("session"),
            user_id=user_id,
            created_at=now,
            expires_at=expires_at,
        )
        return self._repo.create_session(session)

    def _determine_setup_state(self, user_id: str) -> str:
        binding = self._repo.get_zhihu_binding(user_id)
        if not binding or binding.binding_status in ("not_started", "skipped", "unavailable", "failed"):
            return "zhihu_pending"
        if binding.binding_status == "expired":
            return "zhihu_pending"
        return "ready"