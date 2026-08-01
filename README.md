# Job Hunter

Job Hunter cerca offerte, le normalizza, assegna un punteggio di compatibilità
spiegabile, elimina ripubblicazioni e invia soltanto gli annunci coerenti con il
profilo. Supporta LinkedIn, Indeed, Adzuna e Remotive.

## Flusso

```text
profile.yaml → fonti → normalizzazione → filtri → ranking
             → deduplicazione → SQLite → email
```

Funzionalità principali:

- ranking 0–100 con motivazioni leggibili;
- keyword obbligatorie, positive e negative;
- esclusione di seniority, corsi, pubblicità e ruoli fuori target;
- rilevamento di contratto ed esperienza dal testo;
- preferenza per il tempo indeterminato;
- distanza e periodo LinkedIn configurabili;
- deduplicazione cross-source e soppressione delle ripubblicazioni;
- regole e pesi personalizzabili tramite YAML;
- email HTML ordinata per compatibilità.

## Installazione

```bash
git clone https://github.com/ar3ac/job_hunter.git
cd job_hunter
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/playwright install chromium
cp profile.example.yaml profile.yaml
```

Creare `.env` partendo da `.env.example`. Le variabili principali sono:

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user
SMTP_PASS=password
MAIL_FROM=mittente@example.com
MAIL_TO=destinatario@example.com
DB_PATH=job_hunter.db
PROFILE_YAML=profile.yaml
```

Per LinkedIn occorre generare una sessione locale autenticata:

```bash
.venv/bin/python src/linkedin_save_state.py
```

## Uso

Esecuzione del profilo completo:

```bash
./run_job_hunter.sh batch
```

Esecuzione CLI semplice:

```bash
./run_job_hunter.sh --sources remotive adzuna --kw python \
  --location Italy --italy-extended --limit 20 --notify
```

## Ranking e configurazione

Le regole globali si trovano sotto `rules`. Ogni ricerca può sovrascriverle con
un blocco `rules` locale.

```yaml
rules:
  minimum_score: 50
  notify_score: 60
  duplicate_window_days: 45
  experience_max_years: 4
  seniority_exclude: [senior, lead, manager]
  hard_exclude: ["corso di formazione", academy, webinar]
  contract_preferred: ["tempo indeterminato", permanent]

searches:
  - name: production_planner
    sources: [linkedin, indeed]
    keywords: ["production planner"]
    required_any: ["production planner", "pianificazione produzione"]
    positive_keywords: [mrp, lean, programmazione]
    exclude_keywords: [software, vendita]
    location: Lecco
    limit: 50
    source_options:
      days: 1
      distance_km: 25
```

`keywords` costruisce la query della fonte. `required_any` decide se il ruolo è
realmente compatibile; `positive_keywords` aumenta il punteggio ed
`exclude_keywords` lo riduce.

Stati prodotti dal ranking:

- `recommended`: alta compatibilità;
- `review`: compatibilità intermedia;
- `rejected`: bassa compatibilità o presenza di segnali negativi.

Durante la fase di calibrazione tutti i nuovi annunci non duplicati vengono
inviati in un'unica email, ordinati per punteggio. Gli stati servono a capire e
affinare il ranking, non a nascondere risultati. Se non ci sono nuovi annunci,
non viene inviata alcuna email.

## Deduplicazione

- chiave forte: fonte + ID originale, poi URL canonico;
- chiave contenuto: titolo + azienda + località reale normalizzati;
- finestra ripubblicazioni configurabile con `duplicate_window_days`;
- `first_seen_at` e `last_seen_at` conservano gli avvistamenti.

Una ripubblicazione resta nello storico ma non genera una nuova email durante la
finestra configurata. La chiave contenuto funziona anche tra fonti diverse.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Deploy sul Raspberry Pi

Il deploy usa SSH, crea un backup SQLite consistente e preserva `.env`,
`profile.yaml`, sessione LinkedIn e modifiche remote non committate. Installa le
dipendenze una volta, esegue i test e una migrazione di smoke.

```bash
./deploy.sh          # aggiorna senza eseguire subito il batch
./deploy.sh --run    # aggiorna e avvia il batch protetto da flock
```

Destinazione e directory sono configurabili:

```bash
JOB_HUNTER_DEPLOY_TARGET=pi@host \
JOB_HUNTER_REMOTE_DIR=/path/to/job_hunter \
./deploy.sh
```

Il cron deve limitarsi a eseguire `run_job_hunter.sh`: le dipendenze non vengono
più aggiornate durante ogni ricerca giornaliera.

## Licenza

[MIT](LICENSE) — Luca Marrazzo
