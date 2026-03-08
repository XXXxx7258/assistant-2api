FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY config.py main.py ./
COPY api/ api/

ENV API_HOST=0.0.0.0
ENV API_PORT=8080

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8080"]
