from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class JobCreateReq(BaseModel):
    kind: Literal["univariate", "multivariate"]
    epochs: int | None = Field(default=None, ge=1, le=200,
                               description="训练轮数；默认 20(univariate)/30(multivariate)，"
                                           "与参考一致时结果可比对")


class JobSummary(BaseModel):
    id: str
    kind: str
    params: dict[str, Any]
    owner: str
    status: Literal["queued", "running", "done", "failed"]
    progress: str
    error: str | None
    created_at: float
    started_at: float | None
    finished_at: float | None
    has_result: bool


class JobDetail(JobSummary):
    result: dict[str, Any] | None = None


class JobListResp(BaseModel):
    jobs: list[JobSummary]


class HealthResp(BaseModel):
    status: str
    service: str
    torch: str
    running_jobs: int
