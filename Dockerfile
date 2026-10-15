FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements-backend.txt requirements-extraction.txt ./
RUN pip install --no-cache-dir -r requirements-backend.txt
COPY backend/ backend/
COPY scripts/ scripts/
COPY config/ config/
COPY database/ database/
COPY alembic.ini ./
COPY tests/fixtures/ tests/fixtures/
COPY docs/examples/dataset-manifest.json docs/examples/dataset-manifest.json
# Public reports are recovered by exact hash, never replaced with sample fixtures.
RUN python scripts/acquire_reports.py && python scripts/rebuild_dataset.py
RUN python -c "from backend.import_dataset import validate_bundle, ROOT; b=validate_bundle(ROOT, 'docs/examples/dataset-manifest.json'); print(len(b['snapshots']), len(b['comparisons']))"
COPY --from=frontend /build/dist /app/frontend/dist
ENV APP_ENV=production API_HOST=0.0.0.0 API_PORT=8000 SENTINEL_FRONTEND_DIR=/app/frontend/dist
RUN useradd --create-home --uid 10001 sentinel && chown -R sentinel:sentinel /app/data
USER sentinel
EXPOSE 8000
CMD ["python", "-m", "backend.bootstrap"]
