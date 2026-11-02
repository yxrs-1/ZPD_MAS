FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY backend /app/backend
COPY src /app/src
WORKDIR /app/backend
ENV UV_HTTP_RETRIES=10
RUN uv sync --frozen --no-dev
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "zpd_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
