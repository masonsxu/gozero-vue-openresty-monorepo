# 鉴权：网关验签后注入 X-User，直接访问（绕过网关）时兜底校验 Bearer JWT
# （HS256），与 user-api 的直连调试行为一致。零第三方依赖（stdlib hmac）。
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def verify_bearer(token: str, secret: str) -> str | None:
    """校验 HS256 JWT 签名与过期时间，成功返回 sub。"""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "HS256":
            return None
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
        exp = payload.get("exp")
        if exp is not None and float(exp) < time.time():
            return None
        sub = payload.get("sub")
        return sub if isinstance(sub, str) and sub else None
    except Exception:  # noqa: BLE001 - 任何解析失败都视为未授权
        return None


def resolve_user(x_user: str, authorization: str) -> str | None:
    if x_user:
        return x_user
    if authorization.startswith("Bearer "):
        secret = os.environ.get("JWT_SECRET", "dev-only-jwt-secret-change-me")
        return verify_bearer(authorization[len("Bearer ") :], secret)
    return None
