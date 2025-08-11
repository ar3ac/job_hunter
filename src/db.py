from __future__ import annotations
import sqlite3
import hashlib
import re
import datetime as dt
import logging


def normalize(s: str) -> str:
    """Pulisce e rende minuscolo un testo per confronti."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[–—/:|]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def hash_strong(source: str, url: str) -> str:
    """Crea un hash univoco basato su fonte e URL."""
    raw = f"{normalize(source)}|{normalize(url)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def hash_soft(title: str, company: str, location: str) -> str:
    """Crea un hash univoco basato su titolo, azienda e località."""
    raw = f"{normalize(title)}|{normalize(company)}|{normalize(location)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def connect(db_path: str = "job_hunter.db") -> sqlite3.Connection:
    """Crea (se non esiste) e connette al database SQLite."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY,
        strong_key TEXT UNIQUE,             -- source+url
        soft_key   TEXT,                    -- title+company+location
        title      TEXT,
        company    TEXT,
        location   TEXT,
        url        TEXT,
        source     TEXT,
        posted_at  TEXT,
        fetched_at TEXT,
        description TEXT
    );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_soft ON jobs(soft_key);")
    conn.commit()
    return conn


def save_jobs(conn: sqlite3.Connection, jobs: list[dict]) -> list[dict]:
    """Inserisce solo i NUOVI. Ritorna la lista dei nuovi inseriti."""
    cur = conn.cursor()
    new_items = []

    for j in jobs:
        strong = hash_strong(j.get("source", ""), j.get(
            "url", "")) if j.get("url") else None
        soft = hash_soft(j.get("title", ""), j.get(
            "company", ""), j.get("location", ""))

        try:
            cur.execute("""
            INSERT OR IGNORE INTO jobs
            (strong_key, soft_key, title, company, location, url, source, posted_at, fetched_at, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strong, soft,
                j.get("title"), j.get("company"), j.get("location"),
                j.get("url"), j.get("source"),
                j.get("posted_at"),
                dt.datetime.utcnow().isoformat(timespec="seconds"),
                j.get("description", "")
            ))
        except sqlite3.Error as e:
            logging.error("DB error: %s", e)
            continue

        if cur.rowcount > 0:
            new_items.append(j)

    conn.commit()
    return new_items
