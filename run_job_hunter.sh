#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR="$HOME/Progetti/job_hunter"
VENV="$PROJECT_DIR/.venv"
cd "$PROJECT_DIR"; source "$VENV/bin/activate"

# Variabili opzionali
export DB_PATH="$PROJECT_DIR/job_hunter.db"
export PROFILE_YAML="$PROJECT_DIR/profile.yaml"

"$VENV/bin/python" "$PROJECT_DIR/src/run_batch.py" >> "$PROJECT_DIR/logs/cron.log" 2>&1
