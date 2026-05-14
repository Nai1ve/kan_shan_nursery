"""In-memory implementation of EnrichmentRepository."""

from __future__ import annotations

from typing import Optional

from .models import EnrichmentJob
from .repository import EnrichmentRepository


class MemoryEnrichmentRepository(EnrichmentRepository):
    """In-memory storage for enrichment jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, EnrichmentJob] = {}

    async def create_job(self, job: EnrichmentJob) -> EnrichmentJob:
        """Create a new enrichment job."""
        self._jobs[job.job_id] = job
        return job

    async def get_job(self, job_id: str) -> Optional[EnrichmentJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    async def get_latest_job(self, user_id: str) -> Optional[EnrichmentJob]:
        """Get the latest job for a user."""
        user_jobs = [j for j in self._jobs.values() if j.user_id == user_id]
        if not user_jobs:
            return None
        return max(user_jobs, key=lambda j: j.created_at)

    async def update_job(self, job: EnrichmentJob) -> EnrichmentJob:
        """Update an existing job."""
        self._jobs[job.job_id] = job
        return job

    async def get_queued_jobs(self) -> list[EnrichmentJob]:
        """Get all jobs with status='queued'."""
        return [j for j in self._jobs.values() if j.status == "queued"]
