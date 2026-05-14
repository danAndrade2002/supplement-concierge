import json
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_STATE_FILE = Path(__file__).parents[5] / ".meli_browser_state.json"
_AFFILIATE_URL = "https://www.mercadolivre.com.br/affiliate-program/api/v2/affiliates/createLink"
_PORTAL_URL = "https://www.mercadolivre.com.br/afiliados/linkbuilder"


async def generate_affiliate_links(product_urls: list[str]) -> dict[str, str]:
    """
    Generate affiliate links for the given product URLs.
    Returns a dict mapping original URL -> affiliate URL.
    Falls back to original URLs on any error.
    """
    if not _STATE_FILE.exists():
        logger.warning("No MELI browser session found. Run refresh_meli_session.py first.")
        return {url: url for url in product_urls}

    tag = settings.MELI_AFFILIATE_TAG
    if not tag:
        logger.warning("MELI_AFFILIATE_TAG not configured; returning plain URLs.")
        return {url: url for url in product_urls}

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=str(_STATE_FILE))
            page = await context.new_page()

            # Navigate to portal so all session cookies (including nsa_rotok) are set
            await page.goto(_PORTAL_URL, wait_until="networkidle", timeout=30_000)

            # Make the fetch from inside the browser — all cookies/headers set automatically
            result = await page.evaluate(
                """
                async ({ urls, tag, endpoint }) => {
                    // Extract _csrf cookie value
                    const csrfCookie = document.cookie
                        .split('; ')
                        .find(c => c.startsWith('_csrf='));
                    const csrfToken = csrfCookie ? decodeURIComponent(csrfCookie.split('=').slice(1).join('=')) : '';

                    const response = await fetch(endpoint, {
                        method: 'POST',
                        credentials: 'include',
                        headers: {
                            'accept': 'application/json, text/plain, */*',
                            'content-type': 'application/json',
                            'x-csrf-token': csrfToken,
                        },
                        body: JSON.stringify({ urls, tag }),
                    });

                    const text = await response.text();
                    return { status: response.status, body: text };
                }
                """,
                {"urls": product_urls, "tag": tag, "endpoint": _AFFILIATE_URL},
            )

            await browser.close()

        status = result.get("status")
        body = result.get("body", "")

        if status != 200:
            logger.warning("Affiliate API error %s: %s", status, body[:300])
            return {url: url for url in product_urls}

        result = json.loads(body)

        # Build mapping: original URL -> affiliate URL
        mapping = {}
        items = result if isinstance(result, list) else result.get("links", result.get("data", []))
        for item in items:
            original = (
                item.get("url")
                or item.get("originalUrl")
                or item.get("original_url", "")
            )
            affiliate = (
                item.get("affiliateUrl")
                or item.get("affiliate_url")
                or item.get("link", "")
            )
            if original and affiliate:
                mapping[original] = affiliate

        # Fall back to original for any unmapped
        for url in product_urls:
            if url not in mapping:
                mapping[url] = url

        return mapping

    except Exception:
        logger.exception("Failed to generate affiliate links via Playwright")
        return {url: url for url in product_urls}
