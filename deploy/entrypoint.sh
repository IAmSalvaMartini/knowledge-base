#!/bin/bash
set -e

# Start cron daemon for scheduled ingest
service cron start

# Run initial ingest on startup
python -m ingest.run &

# Start Flask API (foreground — keeps container alive)
exec python app.py
