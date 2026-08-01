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

# Le dipendenze vengono installate da deploy.sh, non durante ogni esecuzione cron.
if ! python -c 'import bs4, dotenv, playwright, requests, yaml' 2>/dev/null; then
  echo "Dipendenze mancanti: esegui ./deploy.sh oppure pip install -e ." >&2
  exit 1
fi

# Carica .env se presente (funziona anche da cron)
# if [[ -f .env ]]; then
#   set -a
#   # shellcheck disable=SC1091
#   . ./.env
#   set +a
# fi

# Avvia l’app (tutti gli argomenti passati vengono inoltrati)
if [[ "${1:-}" == "batch" ]]; then
    shift
    exec python src/run_batch.py "$@"
else
    exec python src/main.py "$@"
fi
