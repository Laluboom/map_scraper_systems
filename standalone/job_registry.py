"""In-memory background job tracking for the standalone web dashboard."""
from __future__ import annotations

import threading
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Callable


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Job:
    id: str
    kind: str
    label: str
    status: str = "queued"
    message: str = "Queued"
    error: str = ""
    cancel_requested: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    thread: threading.Thread | None = field(default=None, repr=False, compare=False)

    @property
    def is_running(self) -> bool:
        return self.status in {"queued", "running"}

    @property
    def can_cancel(self) -> bool:
        return self.is_running and not self.cancel_requested


class JobRegistry:
    def __init__(self, max_jobs: int = 25):
        self.max_jobs = max_jobs
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    def start(self, kind: str, label: str, target: Callable[[Job], None]) -> Job:
        job = Job(id=str(uuid.uuid4()), kind=kind, label=label)
        with self._lock:
            self._jobs[job.id] = job
            self._order.insert(0, job.id)
            self._trim_locked()

        def _runner():
            self.mark_running(job.id, "Started")
            try:
                target(job)
            except Exception as exc:
                self.mark_failed(job.id, str(exc), traceback.format_exc())
            else:
                current = self.get(job.id)
                if current and current.status == "running":
                    self.mark_complete(job.id, current.message or "Complete")

        thread = threading.Thread(target=_runner, daemon=True)
        job.thread = thread
        thread.start()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def recent(self, kind: str | None = None, limit: int = 10) -> list[Job]:
        with self._lock:
            jobs = [self._jobs[job_id] for job_id in self._order if job_id in self._jobs]
            if kind:
                jobs = [job for job in jobs if job.kind == kind]
            return jobs[:limit]

    def active(self, kind: str | None = None) -> Job | None:
        with self._lock:
            for job_id in self._order:
                job = self._jobs.get(job_id)
                if not job or not job.is_running:
                    continue
                if kind is None or job.kind == kind:
                    return job
        return None

    def update(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.is_running:
                job.message = message

    def request_cancel(self, job_id: str, message: str = "Cancel requested") -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or not job.is_running:
                return False
            job.cancel_requested = True
            job.message = message
            return True

    def is_cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return bool(job and job.cancel_requested)

    def mark_running(self, job_id: str, message: str = "Running") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "running"
                job.started_at = job.started_at or _now()
                job.message = message

    def mark_complete(self, job_id: str, message: str = "Complete") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "complete"
                job.message = message
                job.finished_at = _now()

    def mark_canceled(self, job_id: str, message: str = "Canceled") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "canceled"
                job.message = message
                job.finished_at = _now()

    def mark_failed(self, job_id: str, message: str, detail: str = "") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "failed"
                job.message = message
                job.error = detail or message
                job.finished_at = _now()

    def wait(self, job_id: str, timeout: float | None = None) -> bool:
        job = self.get(job_id)
        if not job or not job.thread:
            return False
        job.thread.join(timeout=timeout)
        return not job.thread.is_alive()

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._order.clear()

    def _trim_locked(self) -> None:
        while len(self._order) > self.max_jobs:
            old_id = self._order.pop()
            job = self._jobs.get(old_id)
            if job and job.is_running:
                self._order.insert(0, old_id)
                break
            self._jobs.pop(old_id, None)


jobs = JobRegistry()
