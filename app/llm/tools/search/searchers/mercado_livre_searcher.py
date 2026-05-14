import logging
from pathlib import Path

import httpx

from app.config import settings
from app.llm.tools.search.searchers.searcher_interface import MarketplaceSearcher

logger = logging.getLogger(__name__)

_PRODUCTS_SEARCH_URL = "https://api.mercadolibre.com/products/search"
_PRODUCT_ITEMS_URL = "https://api.mercadolibre.com/products/{product_id}/items"
_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
_CATALOG_URL = "https://www.mercadolivre.com.br/p/{product_id}"
_MAX_RESULTS = 10
_ENV_FILE = Path(__file__).parents[6] / ".env"

_cached_access_token: str = ""


def _matches_exclusions(title: str, exclude_ingredients: list[str]) -> bool:
    if not exclude_ingredients:
        return False
    lower = title.lower()
    return any(ing.strip().lower() in lower for ing in exclude_ingredients if ing.strip())


def _update_env_tokens(access_token: str, refresh_token: str) -> None:
    try:
        text = _ENV_FILE.read_text()
        for key, value in (("MELI_ACCESS_TOKEN", access_token), ("MELI_REFRESH_TOKEN", refresh_token)):
            if f"{key}=" in text:
                lines = text.splitlines()
                text = "\n".join(
                    f"{key}={value}" if line.startswith(f"{key}=") else line
                    for line in lines
                ) + "\n"
            else:
                text = text.rstrip("\n") + f"\n{key}={value}\n"
        _ENV_FILE.write_text(text)
    except Exception:
        logger.warning("Could not persist MELI tokens to .env", exc_info=True)


async def _refresh_access_token(client: httpx.AsyncClient) -> str:
    global _cached_access_token
    refresh_token = settings.MELI_REFRESH_TOKEN
    if not refresh_token:
        logger.warning("No MELI_REFRESH_TOKEN configured — run auth_meli.py first")
        return ""
    try:
        response = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": settings.MELI_CLIENT_ID,
                "client_secret": settings.MELI_CLIENT_SECRET,
                "refresh_token": refresh_token,
            },
            headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
        new_access = data["access_token"]
        new_refresh = data.get("refresh_token", refresh_token)
        _cached_access_token = new_access
        _update_env_tokens(new_access, new_refresh)
        logger.info("MELI access token refreshed")
        return new_access
    except Exception:
        logger.exception("Failed to refresh MELI access token")
        return ""


async def _get_access_token(client: httpx.AsyncClient) -> str:
    global _cached_access_token
    if _cached_access_token:
        return _cached_access_token
    if settings.MELI_ACCESS_TOKEN:
        _cached_access_token = settings.MELI_ACCESS_TOKEN
        return _cached_access_token
    return await _refresh_access_token(client)


async def _fetch_min_price(client: httpx.AsyncClient, product_id: str, headers: dict) -> float | None:
    """Fetch the cheapest active listing price for a catalog product."""
    try:
        url = _PRODUCT_ITEMS_URL.format(product_id=product_id)
        resp = await client.get(url, params={"status": "active", "limit": 5}, headers=headers)
        if resp.status_code != 200:
            return None
        items = resp.json().get("results", [])
        prices = [item["price"] for item in items if item.get("price") is not None]
        return float(min(prices)) if prices else None
    except Exception:
        logger.debug("Could not fetch price for product %s", product_id)
        return None


class MercadoLivreSearcher(MarketplaceSearcher):
    async def search(self, query: str, exclude_ingredients: list[str]) -> list[dict]:
        if not settings.MELI_CLIENT_ID:
            logger.warning("MELI_CLIENT_ID not configured; skipping Mercado Livre search")
            return []

        async with httpx.AsyncClient(timeout=15.0) as client:
            token = await _get_access_token(client)
            if not token:
                return []

            headers = {"Authorization": f"Bearer {token}"}

            # Step 1: search the catalog for matching products
            resp = await client.get(
                _PRODUCTS_SEARCH_URL,
                params={"site_id": settings.MELI_SITE_ID, "q": query, "limit": _MAX_RESULTS},
                headers=headers,
            )

            if resp.status_code == 401:
                global _cached_access_token
                _cached_access_token = ""
                token = await _refresh_access_token(client)
                if not token:
                    return []
                headers = {"Authorization": f"Bearer {token}"}
                resp = await client.get(
                    _PRODUCTS_SEARCH_URL,
                    params={"site_id": settings.MELI_SITE_ID, "q": query, "limit": _MAX_RESULTS},
                    headers=headers,
                )

            if resp.status_code != 200:
                logger.error("Mercado Livre products search failed (status %s)", resp.status_code)
                return []

            products = resp.json().get("results", [])

            # Step 2: filter by excluded ingredients on the product name
            filtered = [
                p for p in products
                if not _matches_exclusions(p.get("name", ""), exclude_ingredients)
            ]

            # Step 3: parallel-fetch the cheapest listing price for each product
            import asyncio
            price_tasks = [_fetch_min_price(client, p["id"], headers) for p in filtered]
            prices = await asyncio.gather(*price_tasks)

            results = []
            catalog_urls = [_CATALOG_URL.format(product_id=p["id"]) for p in filtered]

            # Generate affiliate links if session is available
            from app.llm.tools.search.searchers.meli_affiliate import generate_affiliate_links
            affiliate_map = await generate_affiliate_links(catalog_urls)

            for product, price, catalog_url in zip(filtered, prices, catalog_urls):
                results.append({
                    "name": product.get("name", "Unknown product"),
                    "price": price if price is not None else float("inf"),
                    "url": affiliate_map.get(catalog_url, catalog_url),
                    "source": "Mercado Livre",
                })

            return results
