# 内存 job 管理：训练任务在后台线程执行，前端轮询状态。
# 最多并行 2 个训练任务（CPU 训练，避免线程超卖），历史保留最近 20 个。
from __future__ import annotations

import threading
import time
import uuid

MAX_CONCURRENT = 2
MAX_HISTORY = 20


class Job:
    def __init__(self, kind: str, params: dict, owner: str):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.params = params
        self.owner = owner
        self.status = "queued"
        self.progress = "queued"
        self.error: str | None = None
        self.result: dict | None = None
        self.created_at = time.time()
        self.started_at: float | None = None
        self.finished_at: float | None = None

    def summary(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "params": self.params,
            "owner": self.owner,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "has_result": self.result is not None,
        }


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._sema = threading.Semaphore(MAX_CONCURRENT)

    def create(self, kind: str, params: dict, owner: str, runner) -> Job:
        job = Job(kind, params, owner)
        with self._lock:
            self._jobs[job.id] = job
            self._prune()
        thread = threading.Thread(target=self._execute, args=(job, runner), daemon=True)
        thread.start()
        return job

    def _execute(self, job: Job, runner) -> None:
        with self._sema:
            job.status = "running"
            job.started_at = time.time()
            try:
                job.result = runner(job)
                job.status = "done"
            except Exception as exc:  # noqa: BLE001 - job 边界需要捕获一切异常
                job.error = f"{type(exc).__name__}: {exc}"
                job.status = "failed"
            finally:
                job.finished_at = time.time()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, owner: str | None = None) -> list[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        if owner is not None:
            jobs = [j for j in jobs if j.owner == owner]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def delete(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status in ("running", "queued"):
                return False
            del self._jobs[job_id]
            return True

    def _prune(self) -> None:
        finished = sorted(
            (j for j in self._jobs.values() if j.status in ("done", "failed")),
            key=lambda j: j.created_at,
        )
        while len(finished) > MAX_HISTORY:
            oldest = finished.pop(0)
            del self._jobs[oldest.id]


manager = JobManager()
