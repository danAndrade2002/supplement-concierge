"""
Run this script once to log in to Mercado Livre and save the browser session.
The saved session is reused headlessly to generate affiliate links.

Usage:
  python refresh_meli_session.py

A browser window will open. Log in to Mercado Livre, then wait — the script
saves your session automatically and closes the browser.
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

STATE_FILE = Path(__file__).parent / ".meli_browser_state.json"
AFFILIATE_URL = "https://www.mercadolivre.com.br/afiliados/linkbuilder"


async def main() -> None:
    print("\n=== Mercado Livre Session Refresh ===\n")
    print("A browser will open. Log in to Mercado Livre if prompted.")
    print("Once you reach the affiliate link builder page, the session is saved automatically.\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(AFFILIATE_URL)

        # Wait until the affiliate builder page loads (user may need to log in first)
        print("Waiting for you to log in and reach the affiliate page...")
        await page.wait_for_url("**/afiliados/**", timeout=120_000)
        # Give the page a moment to fully settle and set all cookies
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        await context.storage_state(path=str(STATE_FILE))
        await browser.close()

    print(f"\nSession saved to {STATE_FILE}")
    print("You can now generate affiliate links automatically.\n")


if __name__ == "__main__":
    asyncio.run(main())
