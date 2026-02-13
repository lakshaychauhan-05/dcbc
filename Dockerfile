# Dockerfile for Unified Calendar Booking Backend
# Includes: Core API + Doctor Portal + Admin Portal + Chatbot
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY run.py .
COPY run_migrations.py .

# Create credentials directory (will be mounted or populated separately)
RUN mkdir -p ./credentials

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run migrations and start server
CMD python run_migrations.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
