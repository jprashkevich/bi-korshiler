# Контент-завод BIG Life. Сборка из корня репозитория:
#   docker build -f content-factory/Dockerfile .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PHOTOS_DIR=/app/images OUTPUT_DIR=/tmp/factory-output

WORKDIR /app/content-factory
COPY content-factory/requirements.txt .
RUN pip install -r requirements.txt \
 && playwright install --with-deps chromium \
 && apt-get update && apt-get install -y --no-install-recommends fonts-noto-core \
 && rm -rf /var/lib/apt/lists/*

COPY images /app/images
COPY content-factory /app/content-factory

CMD ["python", "-m", "factory", "worker"]
