from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit


ROOT_DIR = Path(__file__).resolve().parents[2]


def fetch_indeed_jobs(query,
                      location: str | None = None,
                      *,
                      pages: int = 1,
                      country: str = "it",
                      profile_dir: str | Path = ROOT_DIR / ".indeed_profile",
                      headless: bool = True) -> list[dict]:
    """
    Estrae offerte da Indeed usando Playwright con profilo persistente (cookies salvati).
    Se rileva una challenge anti-bot, solleva un’eccezione con istruzioni per il refresh.
    """
    from playwright.sync_api import sync_playwright

    base = f"https://{country}.indeed.com/jobs"
    q = " ".join(query) if isinstance(query, (list, tuple)) else str(query or "")
    l = location or ""
    out, seen = [], set()

    with sync_playwright() as p:
        # usa il profilo persistente salvato con lo script di refresh
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless,
            locale="it-IT",
        )
        page = ctx.new_page()

        for i in range(pages):
            params = {"q": q, "l": l, "sort": "date"}
            if i:
                params["start"] = i * 10
            url = f"{base}?{urlencode(params)}"
            page.goto(url, wait_until="networkidle", timeout=60000)

            # rileva challenge Cloudflare/recaptcha: cookie scaduti → rinfresca con lo script
            if page.locator('iframe[src*="challenges.cloudflare.com"], iframe[src*="recaptcha"]').count() > 0:
                ctx.close()
                raise RuntimeError(
                    "Blocco anti-bot rilevato. Esegui scripts/indeed_refresh_state.py una volta (headful) e riprova."
                )

            cards = page.query_selector_all("a.tapItem")
            if not cards:
                # layout alternativo mobile come fallback
                cards = page.query_selector_all('a[href*="/m/viewjob"]')

            for c in cards:
                href = c.get_attribute("href") or ""
                if not href:
                    continue
                link = href if href.startswith(
                    "http") else f"https://{country}.indeed.com{href}"
                parsed = urlsplit(link)
                query_values = parse_qs(parsed.query)
                job_id = (query_values.get("jk") or [None])[0]
                canonical = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode({"jk": job_id}) if job_id else "", ""))
                if canonical in seen:
                    continue
                seen.add(canonical)

                t_el = c.query_selector(
                    "h2 span") or c.query_selector("h2.jobTitle span")
                company_el = c.query_selector("span.companyName")
                loc_el = c.query_selector("div.companyLocation")
                date_el = c.query_selector("span.date")

                out.append({
                    "source": "indeed",
                    "id": job_id,
                    "title": (t_el.inner_text().strip() if t_el else c.inner_text().strip()),
                    "company": (company_el.inner_text().strip() if company_el else ""),
                    "location": (loc_el.inner_text().strip() if loc_el else ""),
                    "url": canonical,
                    "published_text": (date_el.inner_text().strip() if date_el else ""),
                })

        ctx.close()
    return out


def fetch_indeed(
    keywords, location=None, limit=30, italy_extended=False, **options
) -> list[dict]:
    del italy_extended
    pages = max(1, min(10, (int(limit) + 9) // 10))
    jobs = fetch_indeed_jobs(
        keywords,
        location,
        pages=pages,
        country=options.get("country", "it"),
        headless=options.get("headless", True),
    )
    return jobs[:max(1, int(limit))]


if __name__ == "__main__":
    # piccolo test
    jobs = fetch_indeed_jobs(
        "python", "Lecco, Lombardia", pages=1, country="it")
    for j in jobs[:10]:
        print(
            f"- {j['title']} @ {j['company']} — {j['location']}\n  {j['url']} [{j['published_text']}]")
