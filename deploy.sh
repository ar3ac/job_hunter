#!/usr/bin/env bash
set -Eeuo pipefail

TARGET="${JOB_HUNTER_DEPLOY_TARGET:-pi@192.168.1.84}"
REMOTE_DIR="${JOB_HUNTER_REMOTE_DIR:-/home/pi/projects/job_hunter}"
RUN_AFTER=false

if [[ "${1:-}" == "--run" ]]; then
  RUN_AFTER=true
elif [[ -n "${1:-}" ]]; then
  echo "Uso: $0 [--run]" >&2
  exit 2
fi

echo "Deploy Job Hunter su ${TARGET}:${REMOTE_DIR}"
ssh "$TARGET" bash -s -- "$REMOTE_DIR" "$RUN_AFTER" <<'REMOTE'
set -Eeuo pipefail
REMOTE_DIR="$1"
RUN_AFTER="$2"
cd "$REMOTE_DIR"

exec 9>/tmp/job_hunter_batch.lock
if ! flock -n 9; then
  echo "Deploy annullato: Job Hunter è in esecuzione." >&2
  exit 1
fi

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_dir="${REMOTE_DIR%/*}/job_hunter_backups/deploy_${timestamp}"
mkdir -p "$backup_dir"

if [[ -f job_hunter.db ]]; then
  python3 - "$backup_dir/job_hunter.db" <<'PY'
import sqlite3
import sys
source = sqlite3.connect("job_hunter.db")
target = sqlite3.connect(sys.argv[1])
with target:
    source.backup(target)
target.close()
source.close()
PY
fi

for file in .env profile.yaml storage_state.json; do
  if [[ -f "$file" ]]; then
    cp -p "$file" "$backup_dir/$file"
  fi
done

if [[ -n "$(git status --porcelain)" ]]; then
  git diff > "$backup_dir/worktree.patch"
  git status --porcelain > "$backup_dir/worktree.status"
  git stash push --include-untracked -m "job-hunter pre-deploy ${timestamp}"
  echo "Modifiche remote preservate in git stash e in $backup_dir"
fi

git fetch origin main
git merge --ff-only origin/main

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --editable .
.venv/bin/playwright install chromium

.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python - <<'PY'
from pathlib import Path
import tempfile
from db import connect
with tempfile.TemporaryDirectory() as directory:
    connection = connect(str(Path(directory) / "smoke.db"))
    connection.close()
print("Smoke test database: OK")
PY

if [[ "$RUN_AFTER" == "true" ]]; then
  ./run_job_hunter.sh batch
fi

echo "Deploy completato. Backup: $backup_dir"
REMOTE
