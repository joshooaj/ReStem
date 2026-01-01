FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/media /app/static

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Pre-collect static files for faster startup (will be refreshed by entrypoint)
RUN python manage.py collectstatic --noinput --clear 2>/dev/null || true

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=muxminus.settings

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run the application via entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
