FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# CRITICAL: Force logs to appear in terminal
ENV PYTHONUNBUFFERED=1

# Increase timeout to 10 minutes
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "--timeout", "600", "--access-logfile", "-", "--error-logfile", "-", "main:app"]