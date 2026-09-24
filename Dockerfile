FROM python:3.11-slim

# Install system dependencies (ffmpeg required by pydub)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Cloud Run automatically injects the PORT environment variable
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
