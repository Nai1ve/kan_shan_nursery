"""PostgreSQL-backed enrichment repository."""

from __future__ import annotations

import json
from typing import Optional

from ..database import get_db_session_factory
from ..models import EnrichmentJobTable
from .models import EnrichmentJob
from .repository import EnrichmentRepository


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _create_id(prefix: str) -> str:
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _row_to_job(row: EnrichmentJobTable) -> EnrichmentJob:
    """Convert database row to domain model."""
    return EnrichmentJob(
        job_id=row.job_id,
        user_id=row.user_id,
        status=row.status,
        trigger=row.trigger,
        include_sources=json.loads(row.include_sources) if row.include_sources else [],
        temporary_profile=json.loads(row.temporary_profile) if row.temporary_profile else None,
        signal_counts=json.loads(row.signal_counts) if row.signal_counts else {},
        memory_update_request_ids=json.loads(row.memory_update_request_ids) if row.memory_update_request_ids else [],
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PostgresEnrichmentRepository(EnrichmentRepository):
    """PostgreSQL storage for enrichment jobs."""

    def __init__(self) -> None:
        self._SessionFactory = get_db_session_factory()

    async def create_job(self, job: EnrichmentJob) -> EnrichmentJob:
        """Create a new enrichment job."""
        session = self._SessionFactory()
        try:
            row = EnrichmentJobTable(
                job_id=job.job_id,
                user_id=job.user_id,
                status=job.status,
                trigger=job.trigger,
                include_sources=json.dumps(job.include_sources, ensure_ascii=False),
                temporary_profile=json.dumps(job.temporary_profile, ensure_ascii=False) if job.temporary_profile else None,
                signal_counts=json.dumps(job.signal_counts, ensure_ascii=False),
                memory_update_request_ids=json.dumps(job.memory_update_request_ids, ensure_ascii=False),
                error_message=job.error_message,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            session.add(row)
            session.commit()
            return job
        finally:
            session.close()

    async def get_job(self, job_id: str) -> Optional[EnrichmentJob]:
        """Get a job by ID."""
        session = self._SessionFactory()
        try:
            row = session.get(EnrichmentJobTable, job_id)
            return _row_to_job(row) if row else None
        finally:
            session.close()

    async def get_latest_job(self, user_id: str) -> Optional[EnrichmentJob]:
        """Get the latest job for a user."""
        session = self._SessionFactory()
        try:
            row = (
                session.query(EnrichmentJobTable)
                .filter_by(user_id=user_id)
                .order_by(EnrichmentJobTable.created_at.desc())
                .first()
            )
            return _row_to_job(row) if row else None
        finally:
            session.close()

    async def update_job(self, job: EnrichmentJob) -> EnrichmentJob:
        """Update an existing job."""
        session = self._SessionFactory()
        try:
            row = session.get(EnrichmentJobTable, job.job_id)
            if not row:
                raise ValueError(f"Job {job.job_id} not found")
            row.status = job.status
            row.include_sources = json.dumps(job.include_sources, ensure_ascii=False)
            row.temporary_profile = json.dumps(job.temporary_profile, ensure_ascii=False) if job.temporary_profile else None
            row.signal_counts = json.dumps(job.signal_counts, ensure_ascii=False)
            row.memory_update_request_ids = json.dumps(job.memory_update_request_ids, ensure_ascii=False)
            row.error_message = job.error_message
            row.updated_at = job.updated_at
            session.commit()
            return job
        finally:
            session.close()

    async def get_queued_jobs(self) -> list[EnrichmentJob]:
        """Get all jobs with status='queued'."""
        session = self._SessionFactory()
        try:
            rows = (
                session.query(EnrichmentJobTable)
                .filter_by(status="queued")
                .order_by(EnrichmentJobTable.created_at.asc())
                .all()
            )
            return [_row_to_job(row) for row in rows]
        finally:
            session.close()
