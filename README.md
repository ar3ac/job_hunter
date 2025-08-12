# Job Hunter

**Job Hunter** è uno script Python modulare per cercare offerte di lavoro online, filtrare in base a parole chiave e località, salvarle in un database ed inviare una notifica email con i nuovi annunci trovati.

Attualmente utilizza come fonte principale l'API di [Remotive](https://remotive.com), ma la struttura è pensata per aggiungere facilmente altre fonti come Adzuna, Indeed, LinkedIn, ecc.

12/08/25 Aggiunto fonte Adzuna e --sources come parametro 
---

## 🚀 Funzionalità

- 🔍 Ricerca per **parole chiave** (es. `python`, `flask`, `developer`).
- 📍 Filtro **località** (client-side), con opzione `--italy-extended` per includere anche annunci Europe/EU.
- 🗄️ Salvataggio in **SQLite** con deduplicazione forte e debole.
- 📧 Invio email in formato HTML con i nuovi annunci trovati.
- 🛡️ Gestione errori e retry automatici sulle richieste API.
- 🕒 Pronto per essere schedulato con **cron** o altri scheduler.

---

## 📦 Installazione

1. Clona il repository:
   ```bash
   git clone https://github.com/ar3ac/job_hunter.git
   cd job_hunter
   ```

2. Crea e attiva un virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Installa in modalità sviluppo:
   ```bash
   pip install -e .
   ```

4. Crea un file `.env` per configurare le credenziali email (esempio in `.env.example`):
   ```env
   SMTP_HOST=smtp.example.com
   SMTP_PORT=587
   SMTP_USER=tuo_username
   SMTP_PASS=tuo_password
   SMTP_FROM=tuo@email.com
   SMTP_TO=destinatario@email.com
   ```

---

## 🛠️ Utilizzo

Esempio di esecuzione:
```bash
python src/main.py --kw python flask --location Italy --italy-extended --limit 20 --notify
```

Parametri principali:
- `--kw` : Lista di parole chiave (default: `python`).
- `--location` : Filtra per località.
- `--italy-extended` : Se location è `Italy`, include anche Europe/EU.
- `--limit` : Numero massimo di annunci per fonte (default: 30).
- `--db` : Percorso database SQLite (default: `job_hunter.db`).
- `--notify` : Invia email con i nuovi annunci.
- `--dry-run` : Non salva nulla, mostra solo i risultati.

---

## 📧 Esempio di email

| Titolo                         | Azienda      | Location     | Link                                  | Data       |
|--------------------------------|--------------|--------------|----------------------------------------|------------|
| Python Developer               | ACME Corp    | Italy        | [link](https://...)                   | 2025-08-11 |
| Backend Engineer               | Tech S.p.A.  | Europe       | [link](https://...)                   | 2025-08-10 |

---

## 🗄️ Database e deduplicazione

- **Chiave forte**: combinazione `source + url` (garantisce unicità dell'annuncio).
- **Chiave debole**: combinazione `title + company + location` (evita duplicati quando l'URL non è presente).
- Gli annunci già presenti non vengono reinseriti, ma possono essere rilevati da altre fonti.

---

## 🛠️ Estendere il progetto

Aggiungere nuove fonti è semplice:
1. Creare un modulo `fetch_<fonte>.py` con una funzione `fetch_<fonte>(...)` che ritorna una lista di dict in formato standard.
2. Integrare la nuova fonte in `main.py` o in un batch runner.
3. Aggiungere eventuali parametri CLI dedicati.

---

## 📅 Esecuzione programmata

Esempio di cron job per eseguire ogni giorno alle 8:00:
```bash
0 8 * * * /percorso/assoluto/.venv/bin/python /percorso/assoluto/src/main.py --kw python flask --location Italy --italy-extended --limit 20 --notify >> /percorso/assoluto/logs/cron.log 2>&1
```

---

## 📜 Licenza

Questo progetto è rilasciato sotto licenza [MIT](LICENSE).

---

**Autore:** [Luca Marrazzo](https://github.com/ar3ac)
