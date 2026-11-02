# --- Frontend build stage ---
FROM node:24-slim@sha256:c86ecead9e55a5210ac1727de38a4ca840bf03dcaf34dc9749addbf383b1920c AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Runtime ---
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/zyranet/backend

# Install runtime deps first (layer caching).
COPY backend/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# Application code and Alembic migrations.
COPY backend/ .

# React SPA built above; FastAPI serves it at /.
COPY --from=frontend /src/frontend/dist ./app/static/spa

# Keep the API and worker unprivileged. The data directory remains writable
# only for the optional legacy topology export when explicitly enabled.
RUN groupadd --system --gid 10001 zyranet \
    && useradd --uid 10001 --gid zyranet --create-home --home-dir /home/zyranet \
       --shell /usr/sbin/nologin zyranet \
    && chown zyranet:zyranet ./app/data
USER 10001:10001

EXPOSE 8000

# Default command runs the API.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
