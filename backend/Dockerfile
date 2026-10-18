FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
RUN useradd --create-home --uid 10001 appuser && mkdir -p /app/data/media && chown -R appuser:appuser /app
USER appuser
EXPOSE 18100
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 18100 --proxy-headers --no-access-log"]
