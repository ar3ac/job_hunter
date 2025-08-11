from __future__ import annotations
import hashlib
import logging
from typing import Any, List, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://remotive.com/api/remote-jobs"


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def _hash_id(title: str, company: str, location: str) -> str:
    raw = f"{(title or '').strip().lower()}|{(company or '').strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _match_location(loc: str, wanted: Optional[str], italy_extended: bool) -> bool:
    if not wanted:
        return True
    loc_l = (loc or "").lower()
    w = wanted.lower()
    if w in loc_l:
        return True
    if italy_extended and w == "italy":
        # accetta annunci europei spesso validi per IT
        for token in ("europe", "eu"):
            if token in loc_l:
                return True
    return False


def fetch_remotive(
    keywords: List[str],
    location_filter: Optional[str] = None,
    limit: int = 50,
    italy_extended: bool = False,
    session: Optional[requests.Session] = None,
) -> List[Dict[str, Any]]:
    """
    Scarica lavori da Remotive filtrando per parole chiave e location (client-side).
    Ritorna una lista di dict normalizzati.
    """
    # pulizia keywords
    kw = [k.strip() for k in (keywords or []) if k and k.strip()]
    query = " ".join(kw) if kw else ""
    params = {"search": query}

    sess = session or make_session()
    logging.debug("Remotive GET %s params=%s", BASE_URL, params)
    resp = sess.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError:
        logging.error("Risposta non-JSON da Remotive (status %s)",
                      resp.status_code)
        return []

    jobs_out: List[Dict[str, Any]] = []
    for j in data.get("jobs", []):
        loc = (j.get("candidate_required_location") or "").strip() or "Remote"
        if not _match_location(loc, location_filter, italy_extended):
            continue

        title = (j.get("title") or "").strip()
        company = (j.get("company_name") or "").strip()
        url = j.get("url") or ""
        posted_at = j.get("publication_date")
        description = j.get("description") or ""
        source_job_id = j.get("id") or j.get("job_id")  # a volte c'è "id"

        jobs_out.append(
            {
                "id": _hash_id(title, company, loc),  # soft id interno
                "title": title,
                "company": company,
                "location": loc,
                "url": url,
                "source": "remotive",
                "posted_at": posted_at,
                "description": description,
                "source_job_id": str(source_job_id) if source_job_id is not None else None,
            }
        )

        if len(jobs_out) >= max(1, int(limit)):
            break

    logging.info("Remotive: restituiti %d annunci (filtrati)", len(jobs_out))
    return jobs_out
