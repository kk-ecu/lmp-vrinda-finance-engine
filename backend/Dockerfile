FROM python:3.12-slim

WORKDIR /app

# WeasyPrint renders HTML -> PDF via native Pango/cairo libraries.
# pdftotext/pdfinfo (poppler-utils) power the rendered-QA text checks.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        libharfbuzz0b \
        libfribidi0 \
        fonts-dejavu-core \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Build context is the repo root (see deploy/docker-compose.prod.yml), so paths
# are prefixed with backend/. This Dockerfile is used for production.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/tests ./tests

# The self-contained extraction engine lives one level up at repo root. The
# compose build context is ./backend, so it is mounted/copied in separately.
# When building standalone, provide it via a bind mount or set EXTRACTION_ENGINE_PATH.

RUN mkdir -p /app/data/database /app/data/sources /app/data/reports /app/data/exports

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
