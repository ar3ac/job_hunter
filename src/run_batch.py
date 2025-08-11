from __future__ import annotations
import os
import sys
import yaml
from dotenv import load_dotenv
from fetch_remotive import fetch_remotive
from db import connect, save_jobs
from report import render_html
from notify import send_email
import logging
import os


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("logs/app.log", encoding="utf-8"),
            logging.StreamHandler()
        ],
    )

def main():
    setup_logging()
    logging.info("Avvio Job Hunter")
    load_dotenv()
    # file profilo dalla root (o da env)
    profile_path = os.getenv("PROFILE_YAML", "profile.yaml")
    if not os.path.exists(profile_path):
        logging.error(f"Profilo non trovato: {profile_path}")
        sys.exit(1)

    with open(profile_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    searches = cfg.get("searches", [])
    if not searches:
        logging.warning("Nessuna ricerca definita in profile.yaml")
        return

    db_path = os.getenv("DB_PATH", "job_hunter.db")
    conn = connect(db_path)

    all_new: list[dict] = []
    total_found = 0

    for s in searches:
        name = s.get("name") or "Ricerca"
        keywords = s.get("keywords") or ["python"]
        location = s.get("location")
        italy_ext = bool(s.get("italy_extended", False))

        jobs = fetch_remotive(keywords, location,
                              limit=100, italy_extended=italy_ext)
        new_jobs = save_jobs(conn, jobs)
        # etichetta per capire da quale ricerca provengono
        for j in new_jobs:
            j["search"] = name
        total_found += len(jobs)
        logging.info(f"[{name}] nuovi inseriti: {len(new_jobs)}")

        all_new.extend(new_jobs)

    if all_new:
        html = render_html(all_new)  # supporta colonna "search" (vedi sotto)
        subject = f"Job Hunter — {len(all_new)} nuovi annunci (batch)"
        send_email(subject, html)
        # salva anche una copia locale per debug
        with open("last_batch_report.html", "w", encoding="utf-8") as f:
            f.write(html)
        logging.info(f"📧 Email inviata. Totale nuovi: {len(all_new)}")
    else:
        logging.info("Nessun nuovo annuncio oggi.")


if __name__ == "__main__":
    main()
