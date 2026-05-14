"""Abstract repository for enrichment jobs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import EnrichmentJob


class EnrichmentRepository(ABC):
    """Abstract base class for enrichment job storage."""

    @abstractmethod
    async def create_job(self, job: EnrichmentJob) -> EnrichmentJob:
        """Create a new enrichment job."""
        ...

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[EnrichmentJob]:
        """Get a job by ID."""
        ...

    @abstractmethod
    async def get_latest_job(self, user_id: str) -> Optional[EnrichmentJob]:
        """Get the latest job for a user."""
        ...

    @abstractmethod
    async def update_job(self, job: EnrichmentJob) -> EnrichmentJob:
        """Update an existing job."""
        ...

    @abstractmethod
    async def get_queued_jobs(self) -> list[EnrichmentJob]:
        """Get all jobs with status='queued'."""
        ...
