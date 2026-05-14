"""Storage layer for UserProfileSnapshot.

PostgreSQL primary, in-memory fallback when DB is unavailable.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from kanshan_shared import load_config

from .snapshot import UserProfileSnapshot

logger = logging.getLogger("kanshan.content.snapshot_repo")

# In-memory fallback
_memory_snapshots: dict[str, UserProfileSnapshot] = {}
_memory_shown: dict[str, set[str]] = {}

_config = load_config()
_db_session_factory = None
_db_available: bool | None = None  # None = not checked yet


def _get_session_factory():
    """Lazy-init database session factory."""
    global _db_session_factory, _db_available
    if _db_available is False:
        return None
    if _db_session_factory is not None:
        return _db_session_factory
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        logger.info("snapshot_db_connecting", extra={"databaseUrl": _config.database_url.split("@")[-1]})
        engine = create_engine(_config.database_url, pool_pre_ping=True, echo=False)
        _db_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        _db_available = True
        logger.info("snapshot_db_connected")
        return _db_session_factory
    except Exception as e:
        logger.warning("snapshot_db_unavailable", extra={"error": str(e)})
        _db_available = False
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SnapshotRepository:
    """Read/write UserProfileSnapshot. PostgreSQL primary, memory fallback."""

    def get_snapshot(self, user_id: str) -> UserProfileSnapshot | None:
        """Get snapshot for a user. Try Redis → PostgreSQL → memory."""
        logger.debug("snapshot_lookup_start", extra={"userId": user_id})

        # Try Redis hot cache first
        snapshot = self._redis_get(user_id)
        if snapshot:
            logger.info("snapshot_hit_redis", extra={
                "userId": user_id,
                "interestIds": snapshot.interest_ids,
                "shownCount": len(snapshot.shown_card_ids),
            })
            return snapshot

        # Try PostgreSQL
        snapshot = self._db_get(user_id)
        if snapshot:
            # Backfill Redis cache
            self._redis_set(user_id, snapshot)
            logger.info("snapshot_hit_db", extra={
                "userId": user_id,
                "interestIds": snapshot.interest_ids,
                "shownCount": len(snapshot.shown_card_ids),
            })
            return snapshot

        # Try memory fallback
        mem_snapshot = _memory_snapshots.get(user_id)
        if mem_snapshot:
            logger.info("snapshot_hit_memory", extra={"userId": user_id})
            return mem_snapshot

        logger.info("snapshot_miss", extra={"userId": user_id})
        return None

    def save_snapshot(self, snapshot: UserProfileSnapshot) -> None:
        """Save snapshot to PostgreSQL + Redis + memory."""
        snapshot.updated_at = _now_iso()

        logger.info("snapshot_save_start", extra={
            "userId": snapshot.user_id,
            "interestIds": snapshot.interest_ids,
            "interests": snapshot.interests,
            "sourceHash": snapshot.source_hash[:8],
            "shownCount": len(snapshot.shown_card_ids),
        })

        # Always keep in memory as ultimate fallback
        _memory_snapshots[snapshot.user_id] = snapshot
        logger.debug("snapshot_saved_memory", extra={"userId": snapshot.user_id})

        # Try PostgreSQL
        self._db_save(snapshot)

        # Try Redis hot cache
        self._redis_set(snapshot.user_id, snapshot)

        logger.info("snapshot_save_done", extra={"userId": snapshot.user_id})

    def get_shown_card_ids(self, user_id: str) -> set[str]:
        """Get shown card IDs for a user."""
        # Try PostgreSQL
        shown = self._db_get_shown(user_id)
        if shown is not None:
            logger.debug("shown_ids_from_db", extra={"userId": user_id, "count": len(shown)})
            return shown

        # Try memory fallback
        mem_shown = _memory_shown.get(user_id, set())
        logger.debug("shown_ids_from_memory", extra={"userId": user_id, "count": len(mem_shown)})
        return mem_shown

    def mark_cards_shown(self, user_id: str, card_ids: list[str]) -> None:
        """Mark cards as shown for a user."""
        if not card_ids:
            return

        logger.info("mark_cards_shown", extra={"userId": user_id, "cardIds": card_ids, "count": len(card_ids)})

        # Update memory fallback
        if user_id not in _memory_shown:
            _memory_shown[user_id] = set()
        _memory_shown[user_id].update(card_ids)

        # Also update snapshot's shown_card_ids
        snapshot = _memory_snapshots.get(user_id)
        if snapshot:
            snapshot.shown_card_ids.update(card_ids)

        # Try PostgreSQL
        self._db_mark_shown(user_id, card_ids)

        # Update Redis cache
        if snapshot:
            self._redis_set(user_id, snapshot)

    # --- Redis helpers ---

    def _redis_get(self, user_id: str) -> UserProfileSnapshot | None:
        try:
            import redis as redis_lib

            r = redis_lib.Redis.from_url(_config.cache.redis_url, decode_responses=True)
            raw = r.get(f"kanshan:content:snapshot:{user_id}")
            if raw:
                logger.debug("snapshot_redis_get_hit", extra={"userId": user_id})
                return UserProfileSnapshot.from_dict(json.loads(raw))
            logger.debug("snapshot_redis_get_miss", extra={"userId": user_id})
        except Exception as e:
            logger.debug("snapshot_redis_get_error", extra={"userId": user_id, "error": str(e)})
        return None

    def _redis_set(self, user_id: str, snapshot: UserProfileSnapshot) -> None:
        try:
            import redis as redis_lib

            r = redis_lib.Redis.from_url(_config.cache.redis_url, decode_responses=True)
            r.setex(
                f"kanshan:content:snapshot:{user_id}",
                3600,  # 1 hour TTL
                json.dumps(snapshot.to_dict(), ensure_ascii=False),
            )
            logger.debug("snapshot_redis_set_ok", extra={"userId": user_id})
        except Exception as e:
            logger.debug("snapshot_redis_set_error", extra={"userId": user_id, "error": str(e)})

    # --- PostgreSQL helpers ---

    def _db_get(self, user_id: str) -> UserProfileSnapshot | None:
        factory = _get_session_factory()
        if not factory:
            return None
        try:
            with factory() as session:
                row = session.execute(
                    "SELECT snapshot FROM content.user_profile_snapshots WHERE user_id = :uid",
                    {"uid": user_id},
                ).fetchone()
                if row:
                    logger.debug("snapshot_db_get_hit", extra={"userId": user_id})
                    return UserProfileSnapshot.from_dict(row[0])
                logger.debug("snapshot_db_get_miss", extra={"userId": user_id})
        except Exception as e:
            logger.warning("snapshot_db_get_failed", extra={"error": str(e)})
        return None

    def _db_save(self, snapshot: UserProfileSnapshot) -> None:
        factory = _get_session_factory()
        if not factory:
            logger.debug("snapshot_db_save_skip_no_db")
            return
        try:
            with factory() as session:
                session.execute(
                    """
                    INSERT INTO content.user_profile_snapshots (user_id, snapshot, updated_at, source_hash)
                    VALUES (:uid, :snap, :updated, :hash)
                    ON CONFLICT (user_id) DO UPDATE SET
                        snapshot = EXCLUDED.snapshot,
                        updated_at = EXCLUDED.updated_at,
                        source_hash = EXCLUDED.source_hash
                    """,
                    {
                        "uid": snapshot.user_id,
                        "snap": json.dumps(snapshot.to_dict(), ensure_ascii=False),
                        "updated": snapshot.updated_at,
                        "hash": snapshot.source_hash,
                    },
                )
                session.commit()
                logger.info("snapshot_db_save_ok", extra={"userId": snapshot.user_id})
        except Exception as e:
            logger.warning("snapshot_db_save_failed", extra={"error": str(e)})

    def _db_get_shown(self, user_id: str) -> set[str] | None:
        factory = _get_session_factory()
        if not factory:
            return None
        try:
            with factory() as session:
                rows = session.execute(
                    "SELECT card_id FROM content.user_shown_cards WHERE user_id = :uid",
                    {"uid": user_id},
                ).fetchall()
                result = {r[0] for r in rows}
                logger.debug("shown_db_get", extra={"userId": user_id, "count": len(result)})
                return result
        except Exception as e:
            logger.warning("snapshot_db_get_shown_failed", extra={"error": str(e)})
        return None

    def _db_mark_shown(self, user_id: str, card_ids: list[str]) -> None:
        factory = _get_session_factory()
        if not factory:
            return
        try:
            with factory() as session:
                for card_id in card_ids:
                    session.execute(
                        """
                        INSERT INTO content.user_shown_cards (user_id, card_id, shown_at)
                        VALUES (:uid, :cid, :now)
                        ON CONFLICT (user_id, card_id) DO NOTHING
                        """,
                        {"uid": user_id, "cid": card_id, "now": _now_iso()},
                    )
                session.commit()
                logger.info("shown_db_mark_ok", extra={"userId": user_id, "count": len(card_ids)})
        except Exception as e:
            logger.warning("snapshot_db_mark_shown_failed", extra={"error": str(e)})
