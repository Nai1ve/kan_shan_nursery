"""Domain models for profile enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProfileSignalSourceItem:
    """A single signal item from OAuth or onboarding data."""

    evidence_id: str
    source_type: str  # onboarding|zhihu_user|followed|followers|moments|manual_content
    source_id: str
    title: Optional[str] = None
    excerpt: Optional[str] = None
    author_name: Optional[str] = None
    headline: Optional[str] = None
    action_text: Optional[str] = None
    published_at: Optional[str] = None
    confidence_hint: float = 0.5


@dataclass
class ProfileSignalBundle:
    """Aggregated signals for LLM profile synthesis."""

    user_id: str
    generated_at: str
    onboarding: dict = field(default_factory=dict)  # selectedInterestIds, writingStyleAnswers, selfDescription
    signals: list[ProfileSignalSourceItem] = field(default_factory=list)


@dataclass
class EnrichmentJob:
    """Enrichment job state."""

    job_id: str
    user_id: str
    status: str = "queued"  # queued|running|completed|failed|fallback
    trigger: str = "oauth_bound"
    include_sources: list[str] = field(default_factory=lambda: ["zhihu_user", "followed", "followers", "moments"])
    temporary_profile: Optional[dict] = None
    signal_counts: dict = field(default_factory=dict)
    memory_update_request_ids: list[str] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
