FROM python:3.12-slim AS base

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml uv.lock README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir -e . --verbose

COPY configs /app/configs
COPY policy /app/policy

ENV IAOPS_CONFIG=/app/configs/indestructibleautoops.pipeline.yaml

ENTRYPOINT ["python", "-m", "indestructibleautoops", "run", "--config", "/app/configs/indestructibleautoops.pipeline.yaml", "--project", "."]
