from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from app.main import app

    # 网关验签后注入 X-User；测试模拟该行为
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(client):
    client.headers.update({"X-User": "admin"})
    return client


def test_health_no_auth(client):
    resp = client.get("/forecast/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "forecast-api"
    assert body["torch"].startswith("2.")


def test_jobs_require_auth(client):
    assert client.get("/forecast/jobs").status_code == 401
    assert client.get("/forecast/jobs/abc").status_code == 401
    assert client.post("/forecast/jobs", json={"kind": "univariate"}).status_code == 401
    assert client.delete("/forecast/jobs/abc").status_code == 401
    assert client.get("/forecast/reference").status_code == 401


def test_direct_bearer_auth(client):
    # 绕过网关直连时用 Bearer 兜底：签一个 HS256 token
    import base64
    import hashlib
    import hmac
    import json
    import os
    import time

    secret = os.environ.get("JWT_SECRET", "dev-only-jwt-secret-change-me")
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "admin", "exp": int(time.time()) + 60}).encode()
    ).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    token = f"{header}.{payload}.{sig}"

    resp = client.get("/forecast/jobs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    # 篡改签名 -> 401
    resp = client.get("/forecast/jobs", headers={"Authorization": f"Bearer {token}x"})
    assert resp.status_code == 401


def test_reference(auth_client):
    resp = auth_client.get("/forecast/reference")
    assert resp.status_code == 200
    body = resp.json()
    assert body["univariate"]["params"] == 74401
    assert set(body["multivariate"]["modes"]) == {"phase_swap", "actuator_lag"}


def test_create_job_invalid_kind(auth_client):
    resp = auth_client.post("/forecast/jobs", json={"kind": "nope"})
    assert resp.status_code == 422


def test_create_job_invalid_epochs(auth_client):
    resp = auth_client.post("/forecast/jobs", json={"kind": "univariate", "epochs": 0})
    assert resp.status_code == 422


def test_univariate_job_lifecycle(auth_client):
    resp = auth_client.post("/forecast/jobs", json={"kind": "univariate", "epochs": 1})
    assert resp.status_code == 201
    job = resp.json()
    assert job["kind"] == "univariate"
    assert job["status"] in ("queued", "running", "done")

    for _ in range(600):
        detail = auth_client.get(f"/forecast/jobs/{job['id']}").json()
        if detail["status"] in ("done", "failed"):
            break
        import time

        time.sleep(0.5)
    assert detail["status"] == "done", detail.get("error")
    assert detail["error"] is None
    result = detail["result"]
    assert result["kind"] == "univariate"
    assert result["epochs"] == 1
    m = result["metrics"]
    assert m["params"] == 74401
    assert m["train_samples"] == 1576 and m["test_samples"] == 394
    for key in ("raw", "loss", "prediction", "residual_histogram", "scatter"):
        assert key in result["series"]
    assert len(result["series"]["raw"]["value"]) == 2000
    # epochs != 20 时给 comparison 但 passed=False
    assert result["comparison"]["epochs_match"] is False

    # list 包含该 job；delete 后 404
    assert any(j["id"] == job["id"] for j in auth_client.get("/forecast/jobs").json()["jobs"])
    assert auth_client.delete(f"/forecast/jobs/{job['id']}").status_code == 204
    assert auth_client.get(f"/forecast/jobs/{job['id']}").status_code == 404


def test_get_missing_job(auth_client):
    assert auth_client.get("/forecast/jobs/doesnotexist").status_code == 404
