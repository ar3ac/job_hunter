import logging
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from pathlib import Path

#STATE_FILE = "storage_state.json"
# la cartella principale del progetto
ROOT_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT_DIR / "storage_state.json"

def fetch_linkedin(keywords, location=None, days=1,limit=30, italy_extended=False):
    seconds = days * 86400
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
        page.goto(url)



        try:
            page.wait_for_selector(
                "div.scaffold-layout__list-detail-container", timeout=10000)
        except Exception:
            logging.warning("⚠️ Nessun job trovato o sessione scaduta.")
            browser.close()
            return []
        
        html = page.content()
        #with open("linkedin_debug.html", "w", encoding="utf-8") as f:
        #    f.write(html)
        
        browser.close()

        # Parse con BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find("div", class_="scaffold-layout__list")
        lu_container = container.find("ul")
        cards = lu_container.find_all("li", recursive=False)
        print(len(cards), "risultati trovati")

        for card in cards[:limit]:
            link_el = card.find("a", class_="job-card-list__title--link")
            company_el = card.find("div", class_="artdeco-entity-lockup__subtitle")

            # A questo punto, possiamo estrarre le informazioni desiderate

            title = link_el.find("strong").text.strip()
            #print("Titolo:", title)
            job_url = link_el['href']
            #print("Link:", job_url[:20])
            company = company_el.text.strip()
            #print("Azienda:", company)

            jobs.append({
                "id": None,
                "title": title,
                "company": company,
                "location": location or "",
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
    jobs = fetch_linkedin(["python","developer"], location="Italy", limit=5)

    print("=== Risultati LinkedIn ===")
    for j in jobs:
        print(f"{j['title']} — {j['company']} ({j['url'][:20]})")


if __name__ == "__main__":
    main()
