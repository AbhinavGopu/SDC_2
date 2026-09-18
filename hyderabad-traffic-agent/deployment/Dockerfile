FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc-dev libpq-dev make curl git && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir poetry
COPY pyproject.toml /app/
RUN poetry config virtualenvs.create false && poetry install --only main
COPY . /app
