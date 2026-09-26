# Stage 1: Build Frontend SPA
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Backend
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv/backend
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin && apt-get clean
COPY backend/requirements.lock.txt ./requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt && useradd --uid 10001 --create-home ayunex && mkdir -p /srv/data/corpus/raw && chown -R ayunex:ayunex /srv/data
COPY --chown=ayunex:ayunex backend/app ./app
COPY --chown=ayunex:ayunex backend/migrations ./migrations
COPY --chown=ayunex:ayunex backend/scripts ./scripts
COPY --chown=ayunex:ayunex backend/alembic.ini ./alembic.ini
COPY --chown=ayunex:ayunex data/corpus/catalog.json /srv/data/corpus/catalog.json
COPY --from=frontend-builder --chown=ayunex:ayunex /app/frontend/dist /srv/frontend/dist
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","2","--no-proxy-headers","--no-access-log"]
