#!/bin/bash
set -e

service postgresql start

until su postgres -c "pg_isready -q"; do
    echo "Waiting for Postgres..."
    sleep 1
done

su postgres -c "psql -c \"ALTER USER postgres PASSWORD 'postgres';\""

su postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname = 'finana'\" | grep -q 1 || psql -c \"CREATE DATABASE finana\""

exec uvicorn main:app --host 0.0.0.0 --port 8000
