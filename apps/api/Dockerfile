# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.12.0 AS uv

FROM python:3.13.14-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app

COPY --from=uv /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.13.14-slim AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/apps/api/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

RUN addgroup --system --gid 10001 shiftbridge \
    && adduser --system --uid 10001 --ingroup shiftbridge --home /nonexistent shiftbridge

COPY --from=builder --chown=shiftbridge:shiftbridge /app/.venv /app/.venv
COPY --chown=shiftbridge:shiftbridge apps/api /app/apps/api

USER shiftbridge
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).read()"]

ENTRYPOINT ["/bin/sh", "/app/apps/api/entrypoint.sh"]
