#!/bin/bash
set -e

echo "=== MuxMinus Frontend Startup ==="

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 muxminus.wsgi:application
