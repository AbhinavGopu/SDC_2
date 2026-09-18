FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends sumo sumo-tools ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH=/usr/share/sumo/tools:/app
ENV SUMO_HOME=/usr/share/sumo
COPY backend /app/backend
COPY simulation /app/simulation
COPY config /app/config
COPY data /app/data
CMD ["python", "-m", "backend.worker"]
