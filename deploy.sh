#!/usr/bin/env bash
# Railway Deploy Script for ClinicOS

set -e  # Exit on error

echo "🚀 Starting Railway deployment for ClinicOS..."

# Check required environment variables
required_vars=(
    "DJANGO_SECRET_KEY"
    "GOOGLE_CLIENT_ID"
    "GOOGLE_CLIENT_SECRET"
    "EMAIL_HOST_USER"
    "EMAIL_HOST_PASSWORD"
)

echo "🔍 Checking required environment variables..."
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    else
        echo "✅ $var is set"
    fi
done

# Run database migrations
echo "🔄 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

# Seed initial data (only runs if needed)
echo "🌱 Seeding initial data..."
python manage.py seed_admin
python manage.py seed_doctors

echo "✅ Deployment preparation complete!"
echo "🚀 Starting Gunicorn..."

# Start Gunicorn (Railway will run this via Procfile)
exec gunicorn clinic_auth.wsgi --bind 0.0.0.0:$PORT --workers 1 --timeout 30