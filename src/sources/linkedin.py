import logging
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from pathlib import Path
import time
#STATE_FILE = "storage_state.json"
# la cartella principale del progetto
ROOT_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT_DIR / "storage_state.json"

def fetch_linkedin(keywords, location=None, limit=30, italy_extended=False, days=1):
    seconds = days * 86400
    print(days, "giorni =", seconds, "secondi")
    tpr = f"&f_TPR=r{seconds}" if days else ""
    #url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}{tpr}"
    """
    Scraper LinkedIn Jobs (versione sync).
    Usa lo storage_state.json per rimanere loggato.
    Ritorna una lista di dict compatibili col DB.
    """
    jobs = []

    with sync_playwright() as p:
        # False per debug, vedi il browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()

        # Costruzione URL base
        kw = "+".join(keywords)
        loc = location or ""
        url = f"https://www.linkedin.com/jobs/search/?keywords={kw}&location={loc}{tpr}"
        logging.info("🌐 Apro LinkedIn Jobs: %s", url)
        page.goto(url, timeout=60000, wait_until="domcontentloaded")

        page.wait_for_selector("div.scaffold-layout__list")
        page.wait_for_timeout(3000)  # attesa extra per caricamento

        container = page.query_selector("div.scaffold-layout__list > div")
        if container:
            for _ in range(10):   # quante “paginazioni” vuoi
                container.evaluate("el => el.scrollBy(0, 600)")  # step più piccolo
                page.wait_for_timeout(1500)  # dai tempo a LinkedIn di caricare
            logging.info("✅ Scroll graduale completato")
        else:
            logging.warning("⚠️ Contenitore scroll non trovato")


        # try:
        #     page.wait_for_selector(
        #         "div.scaffold-layout__list-detail-container", timeout=30000)
        # except Exception:
        #     logging.warning("⚠️ Nessun job trovato o sessione scaduta.")
        #     browser.close()
        #     return []
        
        html = page.content()
        # with open("linkedin_debug.html", "w", encoding="utf-8") as f:
        #    f.write(html)
        
        browser.close()

        # Parse con BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find("div", class_="scaffold-layout__list")
        lu_container = container.find("ul")
        cards = lu_container.find_all("li", recursive=False)
        print(len(cards), "risultati trovati")
        #time.sleep(50)  # per sicurezza, evita problemi di rate limit
        for card in cards[:limit]:
            link_el = card.find("a", class_="job-card-list__title--link")
            #print(card)
            print(len(link_el), type(link_el))
            company_el = card.find("div", class_="artdeco-entity-lockup__subtitle")
            location_el = card.find("ul", class_="job-card-container__metadata-wrapper")
            # A questo punto, possiamo estrarre le informazioni desiderate
            #print(link_el)
            title = link_el.find("strong").text.strip()
            #print("Titolo:", title)
            job_url = link_el['href']
            #print("Link:", job_url[:20])
            company = company_el.text.strip()
            #print("Azienda:", company)
            loc_company = location_el.text.strip()
            #print("Location Azienda:", loc_company)
            jobs.append({
                "id": None,
                "title": title,
                "company": company,
                "location": location or "",
                "loc_company": loc_company,
                "url": "https://www.linkedin.com" + job_url,
                "source": "linkedin",
                "posted_at": None,
                "description": ""
            })
    

    return jobs


# Funzione main per test standalone
def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    jobs = fetch_linkedin(["magazziniere"], location="Lecco", limit=50)

    print("=== Risultati LinkedIn ===")
    for j in jobs:
        print(f"{j['title']} — {j['company']} - {j['loc_company']} - ({j['url'][:40]})")


if __name__ == "__main__":
    main()
