from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup


ROOT_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT_DIR / "storage_state.json"


def _clean_job_url(href: str) -> str:
    absolute = urljoin("https://www.linkedin.com", href)
    parsed = urlsplit(absolute)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def _job_id(url: str) -> str | None:
    match = re.search(r"/jobs/view/(\d+)", url)
    if match:
        return match.group(1)
    m = re.search(r"-(\d+)(?:\?|$)", url)
    if m:
        return m.group(1)
    return None


def _text(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def parse_job_cards(html: str, location: str | None, limit: int) -> list[dict]:
    """Parser puro e testabile della lista LinkedIn."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[dict] = []

    # 1. Prova il layout per utente loggato
    list_container = soup.find("div", class_="scaffold-layout__list")
    if list_container:
        ul = list_container.find("ul")
        cards = ul.find_all("li", recursive=False) if ul else []
        for card in cards:
            link = card.find("a", class_="job-card-list__title--link")
            if not link or not link.get("href"):
                continue
            title = _text(link.find("strong")) or _text(link)
            company = _text(card.find("div", class_="artdeco-entity-lockup__subtitle"))
            location_actual = _text(
                card.find("ul", class_="job-card-container__metadata-wrapper")
            )
            if not title:
                continue
            job_url = _clean_job_url(link["href"])
            jobs.append({
                "id": _job_id(job_url),
                "title": title,
                "company": company,
                "location": location_actual or location or "",
                "location_actual": location_actual,
                "loc_company": location_actual,
                "url": job_url,
                "source": "linkedin",
                "posted_at": None,
                "description": "",
            })
            if len(jobs) >= max(1, int(limit)):
                break
        return jobs

    # 2. Prova il layout pubblico (utente non loggato o authwall bypassato)
    ul = soup.find("ul", class_="jobs-search__results-list")
    if ul:
        cards = ul.find_all("li", recursive=False)
        for card in cards:
            link = card.find("a", class_="base-card__full-link")
            if not link or not link.get("href"):
                continue
            title_node = card.find("h3", class_="base-search-card__title")
            title = _text(title_node) or _text(card.find("span", class_="sr-only"))
            company_node = card.find("h4", class_="base-search-card__subtitle")
            company = _text(company_node)
            location_node = card.find("span", class_="job-search-card__location")
            location_actual = _text(location_node)
            if not title:
                continue
            
            job_url = _clean_job_url(link["href"])
            jobs.append({
                "id": _job_id(job_url),
                "title": title,
                "company": company,
                "location": location_actual or location or "",
                "location_actual": location_actual,
                "loc_company": location_actual,
                "url": job_url,
                "source": "linkedin",
                "posted_at": None,
                "description": "",
            })
            if len(jobs) >= max(1, int(limit)):
                break
        return jobs

    return jobs


def fetch_linkedin(
    keywords,
    location=None,
    limit=30,
    italy_extended=False,
    days=1,
    distance_km=10,
    enrich_details=True,
    detail_limit=20,
    detail_terms=None,
):
    """Raccoglie e normalizza le offerte LinkedIn della pagina risultati."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    del italy_extended  # LinkedIn applica direttamente il filtro location.
    params = {
        "keywords": " ".join(str(k) for k in keywords if k),
        "location": location or "",
        "distance": max(0, int(distance_km)),
    }
    if days:
        params["f_TPR"] = f"r{int(days) * 86400}"
    url = f"https://www.linkedin.com/jobs/search/?{urlencode(params)}"
    jobs: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(storage_state=STATE_FILE)
            page = context.new_page()
            logging.info("🌐 Apro LinkedIn Jobs: %s", url)
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            try:
                page.wait_for_selector("div.scaffold-layout__list, ul.jobs-search__results-list", timeout=30000)
            except PlaywrightTimeoutError as exc:
                if "/login" in page.url or "checkpoint" in page.url:
                    raise RuntimeError("Sessione LinkedIn scaduta: rigenerare storage_state.json") from exc
                raise RuntimeError("Lista offerte LinkedIn non caricata") from exc

            container = page.query_selector("div.scaffold-layout__list > div")
            if container:
                for index in range(10):
                    try:
                        container.evaluate("el => el.scrollBy(0, 600)")
                        logging.debug("Scroll LinkedIn %d/10", index + 1)
                        page.wait_for_timeout(1200)
                    except Exception:
                        break
            else:
                for index in range(10):
                    try:
                        page.evaluate("window.scrollBy(0, 600)")
                        page.wait_for_timeout(1200)
                    except Exception:
                        break

            jobs = parse_job_cards(page.content(), location, limit)
            logging.info("LinkedIn: %d offerte normalizzate", len(jobs))

            # Arricchisce solo candidati con una keyword già presente nel titolo:
            # evita visite inutili a pubblicità e raccomandazioni palesemente fuori target.
            if enrich_details:
                terms = [
                    str(term).casefold()
                    for term in (detail_terms or keywords)
                    if term
                ]
                candidates = [
                    job for job in jobs
                    if any(term in job["title"].casefold() for term in terms)
                ][:max(0, int(detail_limit))]
                detail_page = context.new_page()
                for job in candidates:
                    try:
                        detail_page.goto(
                            job["url"], timeout=45000, wait_until="domcontentloaded"
                        )
                        description = detail_page.locator(
                            ".jobs-description-content__text, .jobs-description, article.jobs-description__container"
                        ).first
                        if description.count():
                            job["description"] = description.inner_text(timeout=5000).strip()
                        criteria = detail_page.locator(
                            ".job-details-jobs-unified-top-card__job-insight, "
                            ".jobs-unified-top-card__job-insight"
                        ).all_inner_texts()
                        if criteria:
                            job["description"] += "\n" + "\n".join(criteria)
                    except Exception as exc:
                        logging.warning("Dettaglio LinkedIn non disponibile per %s: %s", job["url"], exc)
                detail_page.close()
        finally:
            browser.close()

    return jobs


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for job in fetch_linkedin(["magazziniere"], location="Lecco", limit=10):
        print(f"{job['title']} — {job['company']} — {job['location_actual']}")


if __name__ == "__main__":
    main()
