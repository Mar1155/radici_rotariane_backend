# Django REST API Template - Docker Setup

FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install Python dependencies
RUN uv sync

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["sh", "-c", "uv run python manage.py migrate && uv run python manage.py runserver 0.0.0.0:8000"]
