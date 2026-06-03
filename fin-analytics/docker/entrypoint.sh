#!/bin/bash
set -e

# Start Postgres
service postgresql start

# Wait until Postgres is actually ready to accept connections
until pg_isready -q; do
    echo "Waiting for Postgres..."
    sleep 1
done

# Create the database if it doesn't exist
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'finana'" | grep -q 1 || \
    psql -U postgres -c "CREATE DATABASE finana"

# Start FastAPI
exec uvicorn main:app --host 0.0.0.0 --port 8000
