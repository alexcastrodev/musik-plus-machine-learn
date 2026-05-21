# BeatNet 1.1.0 pins numba==0.54.1 which has no Python 3.11 build
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analyze.py .

VOLUME ["/stems", "/audio", "/analysis"]
ENTRYPOINT ["python", "/app/analyze.py"]
