"""PostgreSQL-backed auth repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..database import get_db_session_factory
from ..models import SessionTable, UserTable, ZhihuBindingTable
from .models import LoginTicket, User, UserSession, ZhihuBinding


class PostgresAuthRepository:
    def __init__(self) -> None:
        self._SessionFactory = get_db_session_factory()
        self._login_tickets: dict[str, LoginTicket] = {}

    def create_user(self, user: User) -> User:
        session = self._SessionFactory()
        try:
            row = UserTable(
                user_id=user.user_id,
                nickname=user.nickname,
                email=user.email,
                username=user.username,
                password_hash=user.password_hash,
                created_at=user.created_at,
                setup_state=user.setup_state,
            )
            session.merge(row)
            session.commit()
            return user
        finally:
            session.close()

    def get_user_by_id(self, user_id: str) -> User | None:
        session = self._SessionFactory()
        try:
            row = session.get(UserTable, user_id)
            if not row:
                return None
            return User(row.user_id, row.nickname, row.email, row.username, row.password_hash, row.created_at, row.setup_state or "zhihu_pending")
        finally:
            session.close()

    def get_user_by_email(self, email: str) -> User | None:
        session = self._SessionFactory()
        try:
            row = session.query(UserTable).filter_by(email=email).first()
            if not row:
                return None
            return User(row.user_id, row.nickname, row.email, row.username, row.password_hash, row.created_at, row.setup_state or "zhihu_pending")
        finally:
            session.close()

    def get_user_by_username(self, username: str) -> User | None:
        session = self._SessionFactory()
        try:
            row = session.query(UserTable).filter_by(username=username).first()
            if not row:
                return None
            return User(row.user_id, row.nickname, row.email, row.username, row.password_hash, row.created_at, row.setup_state or "zhihu_pending")
        finally:
            session.close()

    def get_user_by_zhihu_uid(self, zhihu_uid: str) -> User | None:
        session = self._SessionFactory()
        try:
            binding = session.query(ZhihuBindingTable).filter_by(zhihu_uid=zhihu_uid).first()
            if not binding:
                return None
            row = session.get(UserTable, binding.user_id)
            if not row:
                return None
            return User(row.user_id, row.nickname, row.email, row.username, row.password_hash, row.created_at, row.setup_state or "zhihu_pending")
        finally:
            session.close()

    def create_session(self, sess: UserSession) -> UserSession:
        session = self._SessionFactory()
        try:
            row = SessionTable(
                session_id=sess.session_id,
                user_id=sess.user_id,
                created_at=sess.created_at,
                expires_at=sess.expires_at,
            )
            session.merge(row)
            session.commit()
            return sess
        finally:
            session.close()

    def get_session(self, session_id: str) -> UserSession | None:
        session = self._SessionFactory()
        try:
            row = session.get(SessionTable, session_id)
            if not row:
                return None
            return UserSession(row.session_id, row.user_id, row.created_at, row.expires_at or "")
        finally:
            session.close()

    def delete_session(self, session_id: str) -> None:
        session = self._SessionFactory()
        try:
            row = session.get(SessionTable, session_id)
            if row:
                session.delete(row)
                session.commit()
        finally:
            session.close()

    def get_zhihu_binding(self, user_id: str) -> ZhihuBinding | None:
        session = self._SessionFactory()
        try:
            row = session.get(ZhihuBindingTable, user_id)
            if not row:
                return None
            return ZhihuBinding(row.user_id, row.zhihu_uid, row.access_token, row.binding_status, row.bound_at, row.expired_at)
        finally:
            session.close()

    def save_zhihu_binding(self, binding: ZhihuBinding) -> ZhihuBinding:
        session = self._SessionFactory()
        try:
            row = ZhihuBindingTable(
                user_id=binding.user_id,
                zhihu_uid=binding.zhihu_uid,
                access_token=binding.access_token,
                binding_status=binding.binding_status,
                bound_at=binding.bound_at,
                expired_at=binding.expired_at,
            )
            session.merge(row)
            session.commit()
            return binding
        finally:
            session.close()

    def update_user_setup_state(self, user_id: str, setup_state: str) -> User | None:
        session = self._SessionFactory()
        try:
            row = session.get(UserTable, user_id)
            if not row:
                return None
            row.setup_state = setup_state
            session.commit()
            return User(row.user_id, row.nickname, row.email, row.username, row.password_hash, row.created_at, row.setup_state or "zhihu_pending")
        finally:
            session.close()

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
