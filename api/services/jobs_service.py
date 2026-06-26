import time
import uuid
from typing import Any

_JOB_TTL_SECONDS = 3600  # keep results for 1h after completion

_jobs: dict[str, dict] = {}


def _gc() -> None:
    now = time.time()
    stale = [jid for jid, job in _jobs.items()
             if job.get("finished_at") and now - job["finished_at"] > _JOB_TTL_SECONDS]
    for jid in stale:
        _jobs.pop(jid, None)


def create_job() -> str:
    _gc()
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "created_at": time.time()}
    return job_id


def set_result(job_id: str, result: Any) -> None:
    if job_id in _jobs:
        _jobs[job_id] = {
            "status": "done",
            "result": result,
            "created_at": _jobs[job_id].get("created_at", time.time()),
            "finished_at": time.time(),
        }


def set_error(job_id: str, error: str) -> None:
    if job_id in _jobs:
        _jobs[job_id] = {
            "status": "error",
            "error": error,
            "created_at": _jobs[job_id].get("created_at", time.time()),
            "finished_at": time.time(),
        }


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)
