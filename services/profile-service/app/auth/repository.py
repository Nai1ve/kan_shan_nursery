from __future__ import annotations

from typing import Any

from .models import User, UserSession, ZhihuBinding


class AuthRepository:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._sessions: dict[str, UserSession] = {}
        self._zhihu_bindings: dict[str, ZhihuBinding] = {}

    def create_user(self, user: User) -> User:
        self._users[user.user_id] = user
        return user

    def get_user_by_id(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def get_user_by_username(self, username: str) -> User | None:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def create_session(self, session: UserSession) -> UserSession:
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> UserSession | None:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def get_zhihu_binding(self, user_id: str) -> ZhihuBinding | None:
        return self._zhihu_bindings.get(user_id)

    def save_zhihu_binding(self, binding: ZhihuBinding) -> ZhihuBinding:
        self._zhihu_bindings[binding.user_id] = binding
        return binding