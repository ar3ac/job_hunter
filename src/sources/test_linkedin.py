import asyncio
from playwright.async_api import async_playwright

STATE_FILE = "/home/ar3ac/Progetti/job_hunter/src/sources/storage_state.json"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        # carica i cookie salvati
        context = await browser.new_context(storage_state=STATE_FILE)
        page = await context.new_page()

        print("🌐 Apro LinkedIn con i cookies salvati...")
        await page.goto("https://www.linkedin.com/")

        # aspetta 10 secondi così puoi controllare a occhio
        await page.wait_for_timeout(10000)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
