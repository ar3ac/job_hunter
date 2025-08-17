from playwright.sync_api import sync_playwright

PROFILE_DIR = ".indeed_profile"  # cartella col profilo persistente
COUNTRY = "it"                   # es: "it", "fr", "de"
QUERY = "python"
LOCATION = "Lecco, Lombardia"


def main():
    url = f"https://{COUNTRY}.indeed.com/jobs?q={QUERY.replace(' ', '+')}&l={LOCATION.replace(' ', '+')}&sort=date"
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,         # finestra visibile per risolvere eventuale check
            locale="it-IT",
        )
        page = ctx.new_page()
        page.goto(url, wait_until="load", timeout=60000)

        print("Se vedi un controllo (Cloudflare/captcha), completalo nella finestra.")
        input(
            "Quando la pagina risultati è visibile, premi Invio qui per salvare lo stato… ")

        # Chiudendo il contesto persistente, cookie & storage restano nella cartella
        ctx.close()
        print("✅ Stato salvato. D’ora in poi puoi usare lo scraper headless.")


if __name__ == "__main__":
    main()
