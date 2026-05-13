from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import LoginTicket, User, UserSession, ZhihuBinding


class AuthRepository:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._sessions: dict[str, UserSession] = {}
        self._zhihu_bindings: dict[str, ZhihuBinding] = {}
        self._login_tickets: dict[str, LoginTicket] = {}

    def create_user(self, user: User) -> User:
        self._users[user.user_id] = user
        return user

    def update_user_setup_state(self, user_id: str, setup_state: str) -> User | None:
        user = self._users.get(user_id)
        if not user:
            return None
        user.setup_state = setup_state
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

    def get_user_by_zhihu_uid(self, zhihu_uid: str) -> User | None:
        for binding in self._zhihu_bindings.values():
            if binding.zhihu_uid == zhihu_uid:
                return self._users.get(binding.user_id)
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

    def create_login_ticket(self, ticket: LoginTicket) -> LoginTicket:
        self._login_tickets[ticket.ticket] = ticket
        return ticket

    def get_login_ticket(self, ticket: str) -> LoginTicket | None:
        return self._login_tickets.get(ticket)

    def consume_login_ticket(self, ticket: str) -> LoginTicket | None:
        item = self._login_tickets.get(ticket)
        if not item or item.consumed_at:
            return None
        item.consumed_at = datetime.now(timezone.utc).isoformat()
        return item

    def delete_expired_login_tickets(self) -> None:
        now = datetime.now(timezone.utc)
        expired: list[str] = []
        for key, ticket in self._login_tickets.items():
            try:
                if datetime.fromisoformat(ticket.expires_at) <= now:
                    expired.append(key)
            except Exception:
                expired.append(key)
        for key in expired:
            self._login_tickets.pop(key, None)
