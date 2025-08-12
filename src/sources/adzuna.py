# sources/adzuna.py
import os
import requests
from datetime import datetime


def fetch_adzuna(kw, location=None, limit=30, italy_extended=False):
    """
    Ritorna una lista di dict con le stesse chiavi che usi per Remotive:
    source, id, title, company, location, url, published_at, salary_min, salary_max, currency, description
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    country = os.getenv("ADZUNA_COUNTRY", "it")
    if not app_id or not app_key:
        raise RuntimeError("Imposta ADZUNA_APP_ID e ADZUNA_APP_KEY in .env")

    # kw può essere lista -> unisci in stringa
    if isinstance(kw, (list, tuple)):
        what = " ".join(str(x) for x in kw if x)
    else:
        what = str(kw or "").strip()

    where = location or ""  # Adzuna accetta stringa vuota

    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    # https://api.adzuna.com/v1/api/jobs/gb/search/1?app_id=71040e54&app_key=9929be2012f2026822fdce45133c6930&what=python%20developer&where=Lombardia&sort_dir=down&sort_by=date
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": what,
        "where": where,
        "results_per_page": int(limit or 30),
        "sort_by": "date",
        "sort_direction": "down",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    out = []
    for it in data.get("results", []):
        created = it.get("created")
        try:
            published = datetime.fromisoformat(
                created.replace("Z", "+00:00")) if created else None
        except Exception:
            published = None

        out.append({
            "source": "adzuna",
            "id": str(it.get("id")),
            "title": it.get("title") or "",
            "company": (it.get("company") or {}).get("display_name"),
            "location": (it.get("location") or {}).get("display_name"),
            "url": it.get("redirect_url") or "",
            "published_at": published,
            "salary_min": it.get("salary_min"),
            "salary_max": it.get("salary_max"),
            "currency": it.get("salary_currency"),
            "description": it.get("description"),
        })
    return out

