#!/usr/bin/env bash
set -Eeuo pipefail

# Vai sempre nella cartella del progetto
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Logs
mkdir -p logs

# Venv
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# Dipendenze
if [[ -f requirements.txt ]]; then
  pip install -U pip >/dev/null
  pip install -r requirements.txt >/dev/null
fi

# Carica .env se presente (funziona anche da cron)
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

# Avvia l’app (tutti gli argomenti passati vengono inoltrati)
exec python src/main.py "$@"

