#!/bin/sh
set -e
cd /app

echo "Initializing database..."
python -c "from api.database import init_db; init_db()"

echo "Seeding admin account (if needed)..."
python scripts/seed_admin.py || true

PORT="${AUTH_API_PORT:-8200}"
echo "Starting Auth API on port ${PORT}..."
exec python -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT}"
