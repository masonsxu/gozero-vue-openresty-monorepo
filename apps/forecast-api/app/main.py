# forecast-api：CNN+Transformer 时间序列预测与耦合失效检测服务。
# 路由前缀 /forecast（网关剥掉 /api 后转发）；鉴权复用网关注入的 X-User。
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, Header, HTTPException, Response

from . import comparison
from .auth import resolve_user
from .jobs import manager
from .ml.multivariate import EPOCHS_DEFAULT as MV_EPOCHS_DEFAULT
from .ml.multivariate import run_multivariate
from .ml.univariate import run_univariate
from .schemas import HealthResp, JobCreateReq, JobDetail, JobListResp, JobSummary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("forecast-api")

app = FastAPI(title="forecast-api", version="0.1.0")


def require_user(
    x_user: str = Header(default=""),
    authorization: str = Header(default=""),
) -> str:
    user = resolve_user(x_user, authorization)
    if not user:
        raise HTTPException(status_code=401, detail={"message": "unauthorized"})
    return user


@app.get("/forecast/health")
def health() -> HealthResp:
    import torch

    running = sum(1 for j in manager.list_jobs() if j.status in ("queued", "running"))
    return HealthResp(status="ok", service="forecast-api", torch=torch.__version__,
                      running_jobs=running)


@app.get("/forecast/reference")
def reference(user: str = Depends(require_user)) -> dict:
    return {
        "univariate": comparison.load_reference("univariate"),
        "multivariate": comparison.load_reference("multivariate"),
    }


@app.post("/forecast/jobs", status_code=201)
def create_job(req: JobCreateReq, user: str = Depends(require_user)) -> JobSummary:
    def runner(job):
        def progress(msg: str) -> None:
            job.progress = msg
            logger.info("job %s: %s", job.id, msg)

        if req.kind == "univariate":
            epochs = req.epochs or 20
            result = run_univariate(epochs, progress)
            result["comparison"] = comparison.compare_univariate(
                result, comparison.load_reference("univariate")
            )
        else:
            epochs = req.epochs or MV_EPOCHS_DEFAULT
            result = run_multivariate(epochs, progress)
            result["comparison"] = comparison.compare_multivariate(
                result, comparison.load_reference("multivariate")
            )
        return result

    job = manager.create(req.kind, {"epochs": req.epochs}, user, runner)
    logger.info("job %s created by %s: kind=%s", job.id, user, req.kind)
    return JobSummary(**job.summary())


@app.get("/forecast/jobs")
def list_jobs(user: str = Depends(require_user)) -> JobListResp:
    return JobListResp(jobs=[JobSummary(**j.summary()) for j in manager.list_jobs()])


@app.get("/forecast/jobs/{job_id}")
def get_job(job_id: str, user: str = Depends(require_user)) -> JobDetail:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"message": "job not found"})
    return JobDetail(**job.summary(), result=job.result)


@app.delete("/forecast/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, user: str = Depends(require_user)) -> Response:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"message": "job not found"})
    if not manager.delete(job_id):
        raise HTTPException(status_code=409, detail={"message": "job still running"})
    return Response(status_code=204)
