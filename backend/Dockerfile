# syntax=docker/dockerfile:1
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_HTTP_TIMEOUT=120 UV_CONCURRENT_DOWNLOADS=4
# Dependencies first, so editing app code does not reinstall them.
COPY pyproject.toml uv.lock ./
# The cache mount keeps downloaded wheels between builds, so a retry after a network hiccup resumes.
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim
RUN useradd --system --create-home --home-dir /home/portfolio portfolio \
    && mkdir /data && chown portfolio /data
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 DATABASE_URL=sqlite:////data/portfolio.db
USER portfolio
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"
# Apply migrations, then serve. One worker: small memory, and SQLite allows one writer anyway.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers"]
