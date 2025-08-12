from __future__ import annotations
import argparse
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from db import connect, save_jobs
from report import render_html
from notify import send_email
from sources import SOURCES



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


def cli() -> None:
    setup_logging()
    logging.info("Avvio Job Hunter")
    load_dotenv()  # carica .env se presente


    parser = argparse.ArgumentParser(
    description="Job Hunter — fonti multiple + DB + notify"
    )
    parser.add_argument("--sources", nargs="+", default=["remotive"],
                    help="Fonti da usare (es: remotive adzuna)")

    parser.add_argument("--kw", nargs="+",
                        default=["python"], help="Parole chiave")
    parser.add_argument("--location", default=None,
                        help="Filtro location (client-side)")
    parser.add_argument("--italy-extended", action="store_true",
                        help="Include Europe/EU quando location=Italy")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--db", default="job_hunter.db")
    parser.add_argument("--notify", action="store_true",
                        help="Invia email con i NUOVI annunci")
    parser.add_argument("--dry-run", action="store_true",
                        help="Non scrive su DB (test)")
    parser.add_argument("--save-html", action="store_true",
                        help="Salva report locale last_report.html")
    args = parser.parse_args()


    # 1) Fetch da una o più fonti
    all_jobs = []
    for name in args.sources:
        fetch = SOURCES.get(name)
        if not fetch:
            logging.warning("Fonte sconosciuta: %s (ignorata)", name)
            continue
        try:
            part = fetch(args.kw, args.location, args.limit, args.italy_extended)
            logging.info("Fonte %s: trovati %d annunci", name, len(part))
            all_jobs.extend(part)
        except Exception as e:
            logging.exception("Errore durante il fetch %s: %s", name, e)

    logging.info("Annunci totali trovati (somma fonti): %d", len(all_jobs))
    jobs = all_jobs

    # 2) Dry-run: niente DB
    if args.dry_run:
        logging.info("Modalità dry-run: non salvo su DB.")
        return

    # 3) Salvataggio + dedup
    conn = None
    try:
        conn = connect(args.db)
        new_jobs = save_jobs(conn, jobs)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                logging.warning("Impossibile chiudere la connessione DB.")

    logging.info("Nuovi trovati: %d", len(new_jobs))
    for j in new_jobs:
        logging.info("- %s — %s (%s)\n  %s",
                     j["title"], j["company"], j["location"], j["url"])

    if not new_jobs:
        logging.info("Nessun nuovo annuncio. Fine.")
        return

    # 4) Report HTML (email + opzionale salvataggio su disco)
    html = render_html(new_jobs)
    if args.save_html:
        with open("last_report.html", "w", encoding="utf-8") as f:
            f.write(html)
        logging.info("💾 Report salvato in last_report.html")

    if args.notify:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        subject = f"[Job Hunter] {len(new_jobs)} nuovi — {date_str}"
        try:
            send_email(subject, html)
            logging.info("📧 Email inviata.")
        except Exception as e:
            logging.exception("Errore invio email: %s", e)


if __name__ == "__main__":
    cli()
