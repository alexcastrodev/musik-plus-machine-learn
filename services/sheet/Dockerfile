FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    lilypond \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY generate_ly.py generate_sheet.py ./

VOLUME ["/analysis", "/output"]
ENTRYPOINT ["python", "/app/generate_sheet.py"]
