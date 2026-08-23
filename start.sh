#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding reference data..."
python -m app.database.seed

echo "Starting bot in webhook mode..."
python -m app.main --webhook
