"""
JobStore: in-memory registry of all jobs + a semaphore that limits how many
Selenium scrape jobs can run at the same time (each one opens a real Chrome
process, so we cap concurrency to protect server RAM).

Also runs a periodic cleanup sweep that deletes job folders that are done
and old, or abandoned mid-way for too long, so disk doesn't fill up on the
free-tier instance.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.jobs.models import JobState, JobStatus

log = logging.getLogger("amr.jobstore")


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}
        self._lock = asyncio.Lock()
        # Caps how many scrape jobs run concurrently. Queued jobs simply wait
        # on this semaphore inside the worker coroutine.
        self.scrape_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCRAPES)

    async def create(self) -> JobState:
        job = JobState()
        job.work_dir = Path(settings.TEMP_ROOT) / job.job_id
        job.work_dir.mkdir(parents=True, exist_ok=True)
        (job.work_dir / "xls").mkdir(exist_ok=True)
        (job.work_dir / "xlsx").mkdir(exist_ok=True)
        (job.work_dir / "charts").mkdir(exist_ok=True)
        async with self._lock:
            self._jobs[job.job_id] = job
        log.info("created job %s", job.job_id)
        return job

    async def get(self, job_id: str) -> Optional[JobState]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def delete(self, job_id: str) -> None:
        async with self._lock:
            job = self._jobs.pop(job_id, None)
        if job and job.work_dir and job.work_dir.exists():
            shutil.rmtree(job.work_dir, ignore_errors=True)
            log.info("deleted job folder for %s", job_id)

    async def cleanup_loop(self) -> None:
        """Background task: run forever, sweep stale jobs every few minutes."""
        while True:
            await asyncio.sleep(settings.CLEANUP_SWEEP_SECONDS)
            try:
                await self._sweep_once()
            except Exception:
                log.exception("cleanup sweep failed")

    async def _sweep_once(self) -> None:
        now = time.time()
        async with self._lock:
            job_ids = list(self._jobs.keys())
        for jid in job_ids:
            job = await self.get(jid)
            if not job:
                continue
            age = now - job.updated_at
            stale_done = job.status in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED) \
                and age > settings.JOB_TTL_AFTER_DONE_SECONDS
            stale_abandoned = age > settings.JOB_TTL_MAX_SECONDS
            if stale_done or stale_abandoned:
                log.info("sweeping stale job %s (age=%.0fs, status=%s)", jid, age, job.status)
                job.clear_credentials()
                await self.delete(jid)


job_store = JobStore()
