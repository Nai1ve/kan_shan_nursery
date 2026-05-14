"""UserProfileSnapshot: persisted user profile for local card selection.

Decouples content-service from real-time profile-service HTTP calls.
A background task syncs profile data into this snapshot; request-time
card selection reads only from the snapshot.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("kanshan.content.snapshot")


@dataclass
class UserProfileSnapshot:
    user_id: str
    interests: list[str] = field(default_factory=list)
    interest_ids: list[str] = field(default_factory=list)
    global_memory: dict[str, Any] = field(default_factory=dict)
    interest_memories: list[dict[str, Any]] = field(default_factory=list)
    following_user_ids: list[str] = field(default_factory=list)
    shown_card_ids: set[str] = field(default_factory=set)
    updated_at: str = ""
    source_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["shown_card_ids"] = sorted(self.shown_card_ids)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfileSnapshot:
        shown = data.get("shown_card_ids", [])
        if isinstance(shown, list):
            shown = set(shown)
        return cls(
            user_id=data["user_id"],
            interests=data.get("interests", []),
            interest_ids=data.get("interest_ids", []),
            global_memory=data.get("global_memory", {}),
            interest_memories=data.get("interest_memories", []),
            following_user_ids=data.get("following_user_ids", []),
            shown_card_ids=shown,
            updated_at=data.get("updated_at", ""),
            source_hash=data.get("source_hash", ""),
        )


def compute_source_hash(profile_data: dict[str, Any]) -> str:
    """Compute a hash of profile data to detect changes."""
    raw = json.dumps(profile_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode()).hexdigest()


def build_snapshot_from_profile(
    profile_data: dict[str, Any],
    user_id: str,
    shown_ids: set[str] | None = None,
) -> UserProfileSnapshot:
    """Build a UserProfileSnapshot from profile-service response."""
    interests = profile_data.get("interests", [])
    interest_memories = profile_data.get("interestMemories", [])
    interest_ids = [m.get("interestId", "") for m in interest_memories if m.get("interestId")]

    logger.info("build_snapshot", extra={
        "userId": user_id,
        "interests": interests,
        "interestIds": interest_ids,
        "memoryCount": len(interest_memories),
        "hasGlobalMemory": bool(profile_data.get("globalMemory")),
        "shownCount": len(shown_ids) if shown_ids else 0,
    })

    return UserProfileSnapshot(
        user_id=user_id,
        interests=interests,
        interest_ids=interest_ids,
        global_memory=profile_data.get("globalMemory", {}),
        interest_memories=interest_memories,
        following_user_ids=[],
        shown_card_ids=shown_ids or set(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        source_hash=compute_source_hash(profile_data),
    )
