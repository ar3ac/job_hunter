from __future__ import annotations
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from db import connect, save_jobs
from report import render_html
from notify import send_email
from sources import SOURCES  # registro fonti (remotive, adzuna, ...)


def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("logs/app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    setup_logging()
    logging.info("Avvio Job Hunter (batch/profile)")

    # Root repo e .env (robusto per cron)
    ROOT_DIR = Path(__file__).resolve().parents[1]
    DOTENV_PATH = ROOT_DIR / ".env"
    load_dotenv(DOTENV_PATH)
    if os.getenv("ADZUNA_APP_ID"):
        logging.info(".env caricato: %s", DOTENV_PATH)

    # Profilo YAML (env o default)
    profile_path = os.getenv("PROFILE_YAML", "profile.yaml")
    profile_path = (ROOT_DIR / profile_path).resolve()
    if not profile_path.exists():
        logging.error("Profilo non trovato: %s", profile_path)
        sys.exit(1)

    with profile_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    searches = cfg.get("searches", [])
    if not searches:
        logging.warning("Nessuna ricerca definita in profile.yaml")
        return

    # DB unico per tutto il batch
    db_path = os.getenv("DB_PATH", str(ROOT_DIR / "job_hunter.db"))
    logging.info("DB path batch: %s", db_path)
    conn = connect(db_path)

    all_new: list[dict] = []
    grand_total_found = 0

    try:
        for s in searches:
            search_name = s.get("name") or "Ricerca"
            keywords = s.get("keywords") or ["python"]
            location = s.get("location")
            italy_ext = bool(s.get("italy_extended", False))
            limit = int(s.get("limit", 100))
            sources_list = s.get("sources") or ["remotive"]  # default

            logging.info(
                "▶︎ [%s] kw=%s | location=%s | limit=%s | sources=%s",
                search_name, keywords, location, limit, sources_list
            )

            # raccoglie i job da tutte le fonti selezionate
            search_jobs: list[dict] = []
            for src_name in sources_list:
                fetch = SOURCES.get(src_name)
                if not fetch:
                    logging.warning(
                        "Fonte sconosciuta: %s (ignorata)", src_name)
                    continue
                try:
                    part = fetch(keywords, location, limit, italy_ext)
                    logging.info("Fonte %s: trovati %d annunci",
                                 src_name, len(part))
                    search_jobs.extend(part)
                except Exception as e:
                    logging.exception(
                        "Errore durante il fetch %s: %s", src_name, e)

            grand_total_found += len(search_jobs)

            # salvataggio + etichetta di provenienza (nome ricerca)
            new_jobs = save_jobs(conn, search_jobs)
            # se save_jobs non committa internamente, committa qui:
            try:
                conn.commit()
            except Exception:
                logging.exception("Commit fallito")

            for j in new_jobs:
                j["search"] = search_name  # utile nel report/email

            logging.info("[%s] nuovi inseriti in DB: %d",
                         search_name, len(new_jobs))
            all_new.extend(new_jobs)

    finally:
        try:
            conn.close()
        except Exception:
            logging.warning("Impossibile chiudere la connessione DB.")

    logging.info(
        "Totale annunci raccolti (tutte le ricerche/fonti): %d", grand_total_found)
    logging.info("Totale NUOVI inseriti (tutte le ricerche): %d", len(all_new))

    if all_new:
        html = render_html(all_new)  # supporta colonna "search"
        subject = f"Job Hunter — {len(all_new)} nuovi annunci (batch)"
        try:
            send_email(subject, html)
            logging.info("📧 Email inviata.")
        except Exception as e:
            logging.exception("Errore invio email: %s", e)

        out = ROOT_DIR / "last_batch_report.html"
        with out.open("w", encoding="utf-8") as f:
            f.write(html)
        logging.info("💾 Report salvato in %s", out)
    else:
        logging.info("Nessun nuovo annuncio oggi.")


if __name__ == "__main__":
    main()
