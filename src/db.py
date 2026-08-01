import sqlite3
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit
import datetime as dt
import logging
import json


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


def content_key(j: dict) -> str:
    """Identità cross-source: ruolo, azienda e località reale."""
    location = j.get("location_actual") or j.get("loc_company") or j.get("location", "")
    return hash_soft(j.get("title", ""), j.get("company", ""), location)


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
        loc_company TEXT,
        url        TEXT,
        source     TEXT,
        posted_at  TEXT,
        fetched_at TEXT,
        description TEXT
    );
    """)
    columns = {
        "loc_company": "TEXT",
        "content_key": "TEXT",
        "search_name": "TEXT",
        "score": "INTEGER",
        "status": "TEXT",
        "score_reasons": "TEXT",
        "matched_keywords": "TEXT",
        "contract_type": "TEXT",
        "experience_min": "INTEGER",
        "experience_max": "INTEGER",
        "seniority": "TEXT",
        "first_seen_at": "TEXT",
        "last_seen_at": "TEXT",
    }
    existing = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    for name, sql_type in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} {sql_type}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_soft ON jobs(soft_key);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_content ON jobs(content_key);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_score ON jobs(status, score);")
    conn.execute("UPDATE jobs SET content_key = soft_key WHERE content_key IS NULL")
    conn.execute("UPDATE jobs SET first_seen_at = fetched_at WHERE first_seen_at IS NULL")
    conn.execute("UPDATE jobs SET last_seen_at = fetched_at WHERE last_seen_at IS NULL")
    conn.commit()
    return conn


def make_strong_key(j: dict) -> str:
    """Ordine di preferenza: source+id  →  source+canonical_url  →  source+soft_key."""
    source = normalize(j.get("source", ""))
    jid = (j.get("id") or "").strip()          # molti adapter ce l'hanno
    url = canonical_url(j.get("url") or "")
    # Le versioni precedenti deduplicavano LinkedIn tramite URL perché non
    # estraevano l'ID. Manteniamo la stessa chiave per una migrazione silenziosa.
    if source == "linkedin" and url:
        return hash16(f"{source}|{url}")
    if source and jid:
        return hash16(f"{source}|{jid}")
    if source and url:
        return hash16(f"{source}|{url}")
    # fallback: soft
    soft = hash_soft(j.get("title", ""), j.get(
        "company", ""), j.get("location", ""))
    return hash16(f"{source}|{soft}")


def save_jobs(
    conn: sqlite3.Connection,
    jobs: list[dict],
    duplicate_window_days: int = 45,
) -> list[dict]:
    cur = conn.cursor()
    new_items = []

    for j in jobs:
        strong = make_strong_key(j)
        soft = hash_soft(j.get("title", ""), j.get(
            "company", ""), j.get("location", ""))
        posted = j.get("posted_at") or j.get(
            "published_at")  # <-- fix nome campo
        content = content_key(j)
        legacy_content = hash_soft(
            j.get("title", ""), j.get("company", ""),
            j.get("search_location") or j.get("location", ""),
        )
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

        # Una ripubblicazione o lo stesso annuncio su un'altra fonte resta nello
        # storico, ma non viene rinotificato nella finestra configurata.
        cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(
            days=max(0, int(duplicate_window_days))
        )).isoformat(timespec="seconds")
        duplicate = cur.execute(
            """
            SELECT id, status, score FROM jobs
            WHERE content_key IN (?, ?) AND COALESCE(last_seen_at, fetched_at) >= ?
            ORDER BY COALESCE(last_seen_at, fetched_at) DESC LIMIT 1
            """,
            (content, legacy_content, cutoff),
        ).fetchone()
        if duplicate:
            cur.execute(
                """UPDATE jobs SET last_seen_at = ?,
                   score = CASE WHEN COALESCE(score, -1) < ? THEN ? ELSE score END,
                   status = CASE WHEN COALESCE(score, -1) < ? THEN ? ELSE status END,
                   score_reasons = CASE WHEN COALESCE(score, -1) < ? THEN ? ELSE score_reasons END,
                   matched_keywords = CASE WHEN COALESCE(score, -1) < ? THEN ? ELSE matched_keywords END
                   WHERE id = ?""",
                (
                    now, j.get("score", 0), j.get("score"),
                    j.get("score", 0), j.get("status"),
                    j.get("score", 0), json.dumps(j.get("score_reasons") or [], ensure_ascii=False),
                    j.get("score", 0), json.dumps(j.get("matched_keywords") or [], ensure_ascii=False),
                    duplicate[0],
                ),
            )
            if duplicate[1] in {"rejected", "review"} and j.get("status") == "recommended":
                new_items.append(j)
            continue

        try:
            cur.execute("""
            INSERT OR IGNORE INTO jobs
            (strong_key, soft_key, content_key, title, company, location,
             loc_company, url, source, posted_at, fetched_at, description,
             search_name, score, status, score_reasons, matched_keywords,
             contract_type, experience_min, experience_max, seniority,
             first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                strong, soft, content,
                j.get("title"), j.get("company"), j.get("location"),
                j.get("location_actual") or j.get("loc_company"),
                j.get("url"), j.get("source"),
                posted,
                now,
                j.get("description", ""),
                j.get("search"), j.get("score"), j.get("status"),
                json.dumps(j.get("score_reasons") or [], ensure_ascii=False),
                json.dumps(j.get("matched_keywords") or [], ensure_ascii=False),
                j.get("contract_type"), j.get("experience_min"),
                j.get("experience_max"), j.get("seniority"), now, now,
            ))
        except sqlite3.Error as e:
            logging.error("DB error: %s", e)
            continue

        if cur.rowcount > 0:
            new_items.append(j)

    conn.commit()
    return new_items
