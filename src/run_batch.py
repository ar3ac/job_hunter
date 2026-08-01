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
from ranking import apply_evaluation, merge_rules


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
    global_rules = cfg.get("rules", {})
    if not searches:
        logging.warning("Nessuna ricerca definita in profile.yaml")
        return

    # DB unico per tutto il batch
    db_path = os.getenv("DB_PATH", str(ROOT_DIR / "job_hunter.db"))
    logging.info("DB path batch: %s", db_path)
    conn = connect(db_path)

    all_new: list[dict] = []
    grand_total_found = 0
    evaluated_counts = {"recommended": 0, "review": 0, "rejected": 0}
    source_failures: list[str] = []

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
                    source_options = dict(s.get("source_options") or {})
                    part = fetch(
                        keywords, location, limit, italy_ext, **source_options
                    )
                    logging.info("Fonte %s: trovati %d annunci",
                                 src_name, len(part))
                    search_jobs.extend(part)
                except Exception as e:
                    logging.exception(
                        "Errore durante il fetch %s: %s", src_name, e)
                    source_failures.append(f"{search_name}/{src_name}: {e}")

            grand_total_found += len(search_jobs)

            evaluated_jobs = [
                apply_evaluation(job, s, global_rules) for job in search_jobs
            ]
            for job in evaluated_jobs:
                evaluated_counts[job["status"]] += 1

            effective_rules = merge_rules(global_rules, s)
            new_jobs = save_jobs(
                conn,
                evaluated_jobs,
                duplicate_window_days=int(effective_rules["duplicate_window_days"]),
            )
            # se save_jobs non committa internamente, committa qui:
            try:
                conn.commit()
            except Exception:
                logging.exception("Commit fallito")

            recommended = [j for j in new_jobs if j.get("status") == "recommended"]
            logging.info(
                "[%s] nuovi DB=%d | consigliati=%d | review=%d | scartati=%d",
                search_name,
                len(new_jobs),
                len(recommended),
                sum(j.get("status") == "review" for j in new_jobs),
                sum(j.get("status") == "rejected" for j in new_jobs),
            )
            all_new.extend(recommended)

    finally:
        try:
            conn.close()
        except Exception:
            logging.warning("Impossibile chiudere la connessione DB.")

    logging.info(
        "Totale annunci raccolti (tutte le ricerche/fonti): %d", grand_total_found)
    logging.info("Totale nuovi CONSIGLIATI da notificare: %d", len(all_new))
    logging.info("Valutazione risultati: %s", evaluated_counts)

    summary = {
        "found": grand_total_found,
        **evaluated_counts,
        "source_failures": source_failures,
    }
    # Nessuna email quando non ci sono annunci consigliati. Gli errori delle
    # fonti restano nei log e compariranno nel riepilogo solo insieme a offerte.
    if all_new:
        html = render_html(all_new, summary=summary)
        subject = f"Job Hunter — {len(all_new)} nuovi annunci"
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

    if source_failures:
        logging.error("Fonti fallite: %s", " | ".join(source_failures))


if __name__ == "__main__":
    main()
