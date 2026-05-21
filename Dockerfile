# syntax=docker/dockerfile:1
# GPU ASR image (local/server). Auth API: Dockerfile.auth | Full compose: docker-compose.yml
ARG BASE_IMAGE=nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8765 8081
ENV PYTHONUNBUFFERED=1 \
    AUTH_API_URL=http://host.docker.internal:8200 \
    NLP_SERVICE_URL=http://host.docker.internal:8100
CMD ["python3", "realtime_transcriber.py"]
