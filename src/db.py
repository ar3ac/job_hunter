import sqlite3
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit
import datetime as dt
import logging


def normalize(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[–—/:|]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def canonical_url(url: str) -> str:
    """URL senza query/fragment, host lower-case, path 'pulito'."""
    if not url:
        return ""
    u = urlsplit(url)
    # niente query, niente fragment
    return urlunsplit((u.scheme, u.netloc.lower(), u.path.rstrip("/"), "", ""))


def hash16(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def hash_soft(title: str, company: str, location: str) -> str:
    raw = f"{normalize(title)}|{normalize(company)}|{normalize(location)}"
    return hash16(raw)


def connect(db_path: str = "job_hunter.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY,
        strong_key TEXT UNIQUE,             -- chiave di dedup (vedi sotto)
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


def make_strong_key(j: dict) -> str:
    """Ordine di preferenza: source+id  →  source+canonical_url  →  source+soft_key."""
    source = normalize(j.get("source", ""))
    jid = (j.get("id") or "").strip()          # molti adapter ce l'hanno
    url = canonical_url(j.get("url") or "")
    if source and jid:
        return hash16(f"{source}|{jid}")
    if source and url:
        return hash16(f"{source}|{url}")
    # fallback: soft
    soft = hash_soft(j.get("title", ""), j.get(
        "company", ""), j.get("location", ""))
    return hash16(f"{source}|{soft}")


def save_jobs(conn: sqlite3.Connection, jobs: list[dict]) -> list[dict]:
    cur = conn.cursor()
    new_items = []

    for j in jobs:
        strong = make_strong_key(j)
        soft = hash_soft(j.get("title", ""), j.get(
            "company", ""), j.get("location", ""))
        posted = j.get("posted_at") or j.get(
            "published_at")  # <-- fix nome campo

        try:
            cur.execute("""
            INSERT OR IGNORE INTO jobs
            (strong_key, soft_key, title, company, location, url, source, posted_at, fetched_at, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strong, soft,
                j.get("title"), j.get("company"), j.get("location"),
                j.get("url"), j.get("source"),
                posted,
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
