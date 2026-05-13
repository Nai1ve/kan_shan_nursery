from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import base64
import hashlib
import hmac
import json
import logging
import os
from uuid import uuid4

from .models import LoginTicket, User, UserSession, ZhihuBinding, create_id, hash_password, now_iso, verify_password


class AuthError(Exception):
    pass


class AuthService:
    SESSION_TTL_HOURS = 24
    OAUTH_STATE_TTL_SECONDS = 600
    LOGIN_TICKET_TTL_SECONDS = 120

    def __init__(self, repository: AuthRepository, zhihu_adapter_url: str = "http://127.0.0.1:8070") -> None:
        self._repo = repository
        self._zhihu_adapter_url = zhihu_adapter_url
        self._logger = logging.getLogger("kanshan.profile_service.auth")
        self._oauth_state_secret = os.getenv("OAUTH_STATE_SECRET", "kanshan-oauth-state-dev-secret")

    def register(self, nickname: str, password: str, email: str | None = None, username: str | None = None) -> dict[str, Any]:
        if not nickname:
            raise AuthError("nickname is required")
        if not email:
            raise AuthError("email is required")
        if not password or len(password) < 6:
            raise AuthError("password must be at least 6 characters")

        if self._repo.get_user_by_email(email):
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
            setup_state="zhihu_pending",
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

    def get_zhihu_token(self, user_id: str) -> dict[str, Any]:
        """Internal endpoint: return raw access_token for inter-service calls."""
        binding = self._repo.get_zhihu_binding(user_id)
        if not binding or not binding.access_token:
            return {"access_token": None, "zhihu_uid": None, "binding_status": "not_started"}
        return {
            "access_token": binding.access_token,
            "zhihu_uid": binding.zhihu_uid,
            "binding_status": binding.binding_status,
        }

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

    def _state_sign(self, payload_json: str) -> str:
        return hmac.new(self._oauth_state_secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()

    def _state_encode(self, payload: dict[str, Any]) -> str:
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        sig = self._state_sign(payload_json)
        raw = json.dumps({"payload": payload, "sig": sig}, separators=(",", ":"), ensure_ascii=False)
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")

    def _state_decode(self, state: str) -> dict[str, Any]:
        raw = base64.urlsafe_b64decode(state.encode("utf-8")).decode("utf-8")
        parsed = json.loads(raw)
        payload = parsed.get("payload") if isinstance(parsed, dict) else None
        sig = parsed.get("sig") if isinstance(parsed, dict) else None
        if not isinstance(payload, dict) or not isinstance(sig, str):
            raise AuthError("invalid oauth state format")
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        expected = self._state_sign(payload_json)
        if not hmac.compare_digest(sig, expected):
            raise AuthError("oauth state signature mismatch")
        expires_at = int(payload.get("exp", 0) or 0)
        if not expires_at or int(datetime.now(timezone.utc).timestamp()) > expires_at:
            raise AuthError("oauth state expired")
        return payload

    def build_zhihu_oauth_state(self, user_id: str) -> str:
        if not user_id:
            raise AuthError("user_id is required for oauth state")
        payload = {
            "uid": user_id,
            "nonce": uuid4().hex,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(datetime.now(timezone.utc).timestamp()) + self.OAUTH_STATE_TTL_SECONDS,
            "v": 1,
        }
        state = self._state_encode(payload)
        self._logger.info(
            "知乎授权state已生成",
            extra={"用户ID": user_id, "过期秒": self.OAUTH_STATE_TTL_SECONDS, "state长度": len(state)},
        )
        return state

    def parse_zhihu_oauth_state(self, state: str | None) -> str | None:
        if not state:
            return None
        try:
            payload = self._state_decode(state)
            user_id = str(payload.get("uid", "") or "")
            if not user_id:
                raise AuthError("oauth state missing uid")
            self._logger.info("知乎授权state校验通过", extra={"用户ID": user_id})
            return user_id
        except Exception as e:
            self._logger.warning("知乎授权state校验失败", extra={"错误类型": type(e).__name__, "错误信息": str(e)})
            return None

    def exchange_zhihu_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for access token via zhihu-adapter."""
        import json
        import urllib.request
        try:
            self._logger.info(
                "知乎换取Token开始",
                extra={"有授权码": bool(code), "授权码长度": len(code or "")},
            )
            url = f"{self._zhihu_adapter_url}/zhihu/oauth/callback?code={code}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                self._logger.info(
                    "知乎换取Token成功",
                    extra={"返回字段": sorted(list(result.keys())) if isinstance(result, dict) else []},
                )
                return result
        except Exception as e:
            self._logger.exception("知乎换取Token失败", extra={"错误类型": type(e).__name__})
            raise AuthError(f"Failed to exchange code: {e}")

    def get_zhihu_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user info from zhihu-adapter using access token."""
        import json
        import urllib.request
        try:
            self._logger.info(
                "知乎拉取用户信息开始",
                extra={"有访问令牌": bool(access_token), "令牌长度": len(access_token or "")},
            )
            url = f"{self._zhihu_adapter_url}/zhihu/user?access_token={access_token}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                items = result.get("items", []) if isinstance(result, dict) else []

                first: Any = {}
                if isinstance(items, list):
                    first = items[0] if items else {}
                elif isinstance(items, dict):
                    first = items
                else:
                    first = {}

                first_keys = sorted(list(first.keys())) if isinstance(first, dict) else []
                has_raw_uid = bool(first.get("raw", {}).get("uid")) if isinstance(first, dict) else False
                self._logger.info(
                    "知乎拉取用户信息成功",
                    extra={
                        "items类型": type(items).__name__,
                        "条目数": len(items) if isinstance(items, (list, dict)) else 0,
                        "首条字段": first_keys,
                        "有原始UID": has_raw_uid,
                    },
                )

                if not first:
                    return {}
                if isinstance(first, dict) and first.get("raw") and isinstance(first["raw"], dict):
                    return first["raw"]
                return first if isinstance(first, dict) else {}
        except Exception as e:
            self._logger.exception("知乎拉取用户信息失败", extra={"错误类型": type(e).__name__})
            raise AuthError(f"Failed to get user info: {e}")

    def get_zhihu_authorize_url(self) -> dict[str, Any]:
        """Get real Zhihu OAuth authorize URL from zhihu-adapter."""
        import json
        import urllib.request
        try:
            url = f"{self._zhihu_adapter_url}/zhihu/oauth/authorize"
            self._logger.info("请求知乎授权链接", extra={"携带State": False})
            with urllib.request.urlopen(url, timeout=5) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except Exception as e:
            raise AuthError(f"Failed to get authorize URL: {e}")

    def ensure_user_by_zhihu_profile(self, user_info: dict[str, Any]) -> User:
        zhihu_uid = str(user_info.get("uid", "") or "")
        if not zhihu_uid:
            raise AuthError("zhihu uid is required")

        existing = None
        if hasattr(self._repo, "get_user_by_zhihu_uid"):
            existing = self._repo.get_user_by_zhihu_uid(zhihu_uid)
        if existing:
            self._logger.info("知乎用户已存在，复用本地账号", extra={"知乎UID": zhihu_uid, "用户ID": existing.user_id})
            return existing

        nickname = str(user_info.get("fullname", "") or "知乎用户")
        suffix = uuid4().hex[:8]
        user = User(
            user_id=create_id("user"),
            nickname=nickname,
            email=f"zhihu-{zhihu_uid}-{suffix}@kanshan.local",
            username=f"zhihu_{zhihu_uid}_{suffix}",
            password_hash=hash_password(uuid4().hex),
            created_at=now_iso(),
            setup_state="llm_pending",
        )
        self._repo.create_user(user)
        self._logger.info("知乎用户首次登录，已创建本地账号", extra={"知乎UID": zhihu_uid, "用户ID": user.user_id})
        return user

    def create_session_for_user(self, user_id: str) -> UserSession:
        return self._create_session(user_id)

    def create_login_ticket_for_user(self, user_id: str, setup_state_hint: str | None = None) -> LoginTicket:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.LOGIN_TICKET_TTL_SECONDS)
        self._repo.delete_expired_login_tickets()
        ticket = LoginTicket(
            ticket=create_id("ticket"),
            user_id=user_id,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            setup_state_hint=setup_state_hint,
        )
        return self._repo.create_login_ticket(ticket)

    def exchange_login_ticket(self, ticket_value: str) -> dict[str, Any]:
        if not ticket_value:
            raise AuthError("ticket is required")
        self._repo.delete_expired_login_tickets()
        ticket = self._repo.get_login_ticket(ticket_value)
        if not ticket:
            raise AuthError("ticket invalid or expired")
        if ticket.consumed_at:
            raise AuthError("ticket already consumed")
        try:
            expires_at = datetime.fromisoformat(ticket.expires_at)
        except Exception as e:
            raise AuthError("ticket invalid") from e
        if datetime.now(timezone.utc) >= expires_at:
            raise AuthError("ticket invalid or expired")

        consumed = self._repo.consume_login_ticket(ticket_value)
        if not consumed:
            raise AuthError("ticket already consumed")

        user = self._repo.get_user_by_id(consumed.user_id)
        if not user:
            raise AuthError("user not found for ticket")
        session = self._create_session(user.user_id)
        setup_state = consumed.setup_state_hint or self._determine_setup_state(user.user_id)
        return {
            "user": user.to_dict(),
            "session": session.to_dict(),
            "setupState": setup_state,
        }

    def set_user_setup_state(self, user_id: str, setup_state: str) -> None:
        if setup_state not in ("zhihu_pending", "llm_pending", "preferences_pending", "provisional_ready", "ready"):
            raise AuthError("invalid setup state")
        self._repo.update_user_setup_state(user_id, setup_state)

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
        user = self._repo.get_user_by_id(user_id)
        binding = self._repo.get_zhihu_binding(user_id)

        if user and getattr(user, "setup_state", None):
            state = user.setup_state
            if state == "zhihu_pending" and binding and binding.binding_status == "bound":
                self._repo.update_user_setup_state(user_id, "llm_pending")
                return "llm_pending"
            return state

        if not binding or binding.binding_status in ("not_started", "skipped", "unavailable", "failed", "expired"):
            return "zhihu_pending"
        return "llm_pending"
