FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime deps first (layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY . .

EXPOSE 8000

# Default command runs the API. The bot is launched as a separate service
# via docker-compose with a different command.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
