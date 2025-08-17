from playwright.sync_api import sync_playwright


def fetch_indeed_jobs(query: str,
                      location: str,
                      *,
                      pages: int = 1,
                      country: str = "it",
                      profile_dir: str = ".indeed_profile") -> list[dict]:
    """
    Estrae offerte da Indeed usando Playwright con profilo persistente (cookies salvati).
    Se rileva una challenge anti-bot, solleva un’eccezione con istruzioni per il refresh.
    """
    base = f"https://{country}.indeed.com/jobs"
    q = query.replace(" ", "+")
    l = location.replace(" ", "+")
    out, seen = [], set()

    with sync_playwright() as p:
        # usa il profilo persistente salvato con lo script di refresh
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,          # pensato per cron
            locale="it-IT",
        )
        page = ctx.new_page()

        for i in range(pages):
            url = f"{base}?q={q}&l={l}&sort=date" + \
                (f"&start={i*10}" if i else "")
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
                if link in seen:
                    continue
                seen.add(link)

                t_el = c.query_selector(
                    "h2 span") or c.query_selector("h2.jobTitle span")
                company_el = c.query_selector("span.companyName")
                loc_el = c.query_selector("div.companyLocation")
                date_el = c.query_selector("span.date")

                out.append({
                    "source": "indeed",
                    "title": (t_el.inner_text().strip() if t_el else c.inner_text().strip()),
                    "company": (company_el.inner_text().strip() if company_el else ""),
                    "location": (loc_el.inner_text().strip() if loc_el else ""),
                    "url": link,
                    "published_text": (date_el.inner_text().strip() if date_el else ""),
                })

        ctx.close()
    return out


if __name__ == "__main__":
    # piccolo test
    jobs = fetch_indeed_jobs(
        "python", "Lecco, Lombardia", pages=1, country="it")
    for j in jobs[:10]:
        print(
            f"- {j['title']} @ {j['company']} — {j['location']}\n  {j['url']} [{j['published_text']}]")
