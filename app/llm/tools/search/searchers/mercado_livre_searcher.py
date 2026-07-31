import logging

import httpx

from app.config import settings
from app.llm.tools.search.searchers.searcher_interface import MarketplaceSearcher
from app.metrics import track_latency

logger = logging.getLogger(__name__)

_SEARCH_LIMIT = 50
_REQUEST_TIMEOUT = 45.0
_AFFILIATE_LINK_URL = "http://51.79.66.17:3000/affiliate-links"
# The affiliate backend's upstream (Mercado Livre createLink) rejects batches
# above ~30 URLs outright, so keep well under that and only bother generating
# links for the handful of results we'll actually show.
_AFFILIATE_LINK_LIMIT = 5


def _matches_exclusions(title: str, exclude_ingredients: list[str]) -> bool:
    if not exclude_ingredients:
        return False
    lower = title.lower()
    return any(ing.strip().lower() in lower for ing in exclude_ingredients if ing.strip())


@track_latency("meli_affiliate_links")
async def _get_affiliate_links(client: httpx.AsyncClient, urls: list[str]) -> dict[str, str]:
    if not urls:
        return {}
    logger.debug("Requesting affiliate links for %d URL(s): %s", len(urls), urls)
    try:
        resp = await client.post(_AFFILIATE_LINK_URL, json={"urls": urls})
        logger.debug("Affiliate API response %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
        return {
            r["origin_url"]: r["affiliate_link"] if r.get("status") == "success" and r.get("affiliate_link") else r["origin_url"]
            for r in resp.json().get("results", [])
        }
    except Exception:
        logger.warning("Failed to fetch affiliate links (payload=%s)", {"urls": urls}, exc_info=True)
        return {}


async def _call_search_api(client: httpx.AsyncClient, query: str) -> list[dict]:
    params = {"q": query, "limit": _SEARCH_LIMIT}
    url = f"{settings.MELI_SEARCH_BASE_URL}/search"

    try:
        resp = await client.get(url, params=params)
    except (httpx.TimeoutException, httpx.RequestError):
        logger.warning("MELI search request failed (network error)", exc_info=True)
        return []

    if resp.status_code == 200:
        logger.info("MELI search API response %s: %s", resp.status_code, resp.text)
        return resp.json().get("results", [])

    if resp.status_code == 401:
        logger.error(
            "MELI search backend session expired; needs manual re-auth on server: %s",
            resp.text[:500],
        )
        return []

    if resp.status_code == 500:
        logger.warning("MELI search failed with 500, retrying once: %s", resp.text[:500])
        try:
            resp = await client.get(url, params=params)
        except (httpx.TimeoutException, httpx.RequestError):
            logger.warning("MELI search retry failed (network error)", exc_info=True)
            return []
        if resp.status_code == 200:
            logger.info("MELI search API response %s: %s", resp.status_code, resp.text)
            return resp.json().get("results", [])
        logger.error("MELI search failed again after retry (status %s): %s", resp.status_code, resp.text[:500])
        return []

    logger.error("MELI search failed (status %s): %s", resp.status_code, resp.text[:500])
    return []


class MercadoLivreSearcher(MarketplaceSearcher):
    @track_latency("marketplace_api_time")
    async def search(self, query: str, exclude_ingredients: list[str]) -> list[dict]:
        if not query.strip():
            return []

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            logger.info("Querying Mercado Livre search endpoint with query: %s", query)
            items = await _call_search_api(client, query)

            valid = [
                item for item in items
                if item.get("title") and item.get("price") is not None and item.get("url")
            ]

            # Only the cheapest few items end up shown to the user (search_tool
            # sorts by price and takes the top 3), so generate affiliate links
            # for the cheapest candidates rather than the first N in search order.
            cheapest_first = sorted(valid, key=lambda item: item["price"])
            urls = [item["url"] for item in cheapest_first[:_AFFILIATE_LINK_LIMIT]]
            affiliate_map = await _get_affiliate_links(client, urls)

            return [
                {
                    "name": item["title"],
                    "price": item["price"],
                    "url": affiliate_map.get(item["url"], item["url"]),
                    "source": "Mercado Livre",
                }
                for item in valid
            ]
