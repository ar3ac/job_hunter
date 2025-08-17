import asyncio
from playwright.async_api import async_playwright

STATE_FILE = "storage_state.json"


async def main():
    async with async_playwright() as p:
        # Puoi usare chromium, firefox o webkit
        # headless=False -> ti mostra il browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        page = await context.new_page()

        # Vai al login di LinkedIn (o Indeed)
        await page.goto("https://www.linkedin.com/login")

        print("👉 Fai manualmente login nel browser aperto...")
        print("👉 Quando sei dentro alla homepage premi Invio qui nella console.")

        input("Premi Invio quando hai completato il login...")

        # Salva stato sessione
        await context.storage_state(path=STATE_FILE)
        print(f"✅ Stato sessione salvato in {STATE_FILE}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
