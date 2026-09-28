# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

# 先装依赖以利用层缓存（uv.lock 锁定与参考一致的 torch/numpy/sklearn 版本）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY reference ./reference

RUN useradd --create-home app && chown -R app:app /app
USER app

EXPOSE 8000
ENTRYPOINT ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
