import asyncio
import logging
import re
from typing import Any

from creatorsapi_python_sdk import ApiClient, DefaultApi
from creatorsapi_python_sdk.exceptions import ApiException
from creatorsapi_python_sdk.models.item import Item
from creatorsapi_python_sdk.models.search_items_request_content import SearchItemsRequestContent
from creatorsapi_python_sdk.models.search_items_resource import SearchItemsResource

from app.config import settings
from app.llm.tools.search.searchers.searcher_interface import MarketplaceSearcher

logger = logging.getLogger(__name__)

_SEARCH_RESOURCES = [
    SearchItemsResource.ITEM_INFO_DOT_TITLE,
    SearchItemsResource.OFFERS_V2_DOT_LISTINGS_DOT_PRICE,
]


def _item_title(item: Item) -> str:
    if item.item_info and item.item_info.title and item.item_info.title.display_value:
        return item.item_info.title.display_value
    return item.asin or "Unknown product"


def _item_price(item: Item) -> float | None:
    if not item.offers_v2 or not item.offers_v2.listings:
        return None
    for listing in item.offers_v2.listings:
        if listing.price and listing.price.money:
            m = listing.price.money
            if m.amount is not None:
                return float(m.amount)
            if m.display_amount:
                digits = re.sub(r"[^\d.,]", "", m.display_amount)
                if "," in digits and "." in digits:
                    digits = digits.replace(".", "").replace(",", ".")
                elif "," in digits:
                    digits = digits.replace(",", ".")
                try:
                    return float(digits) if digits else None
                except ValueError:
                    pass
    return None


def _item_url(item: Item) -> str:
    if item.detail_page_url:
        return item.detail_page_url
    if item.asin:
        host = settings.AMAZON_MARKETPLACE.replace("www.", "")
        return f"https://www.{host}/dp/{item.asin}"
    return ""


def _matches_exclusions(title: str, exclude_ingredients: list[str]) -> bool:
    if not exclude_ingredients:
        return False
    lower = title.lower()
    return any(ing.strip().lower() in lower for ing in exclude_ingredients if ing.strip())


def _run_amazon_search(query: str) -> list[dict[str, Any]]:
    if not (
        settings.AMAZON_CREATORS_CREDENTIAL_ID
        and settings.AMAZON_CREATORS_CREDENTIAL_SECRET
        and settings.AMAZON_PARTNER_TAG
    ):
        logger.warning(
            "Amazon Creators API not configured; set AMAZON_CREATORS_CREDENTIAL_ID, "
            "AMAZON_CREATORS_CREDENTIAL_SECRET, and AMAZON_PARTNER_TAG"
        )
        return []

    api_client = ApiClient(
        credential_id=settings.AMAZON_CREATORS_CREDENTIAL_ID,
        credential_secret=settings.AMAZON_CREATORS_CREDENTIAL_SECRET,
        version=settings.AMAZON_CREATORS_API_VERSION,
    )
    api = DefaultApi(api_client=api_client)

    request = SearchItemsRequestContent(
        keywords=query,
        partner_tag=settings.AMAZON_PARTNER_TAG,
        item_count=10,
        resources=_SEARCH_RESOURCES,
    )

    try:
        response = api.search_items(
            x_marketplace=settings.AMAZON_MARKETPLACE,
            search_items_request_content=request,
        )
    except ApiException:
        logger.exception("Amazon Creators API search_items failed")
        return []
    except Exception:
        logger.exception("Unexpected error calling Amazon Creators API")
        return []

    out: list[dict[str, Any]] = []
    sr = response.search_result
    if not sr or not sr.items:
        return out

    for item in sr.items:
        if not item:
            continue
        title = _item_title(item)
        price = _item_price(item)
        url = _item_url(item)
        out.append(
            {
                "name": title,
                "price": price if price is not None else float("inf"),
                "url": url,
                "source": "Amazon",
            }
        )
    return out


class AmazonSearcher(MarketplaceSearcher):
    async def search(
        self, query: str, exclude_ingredients: list[str]
    ) -> list[dict]:
        raw = await asyncio.to_thread(_run_amazon_search, query)
        filtered = [
            r
            for r in raw
            if not _matches_exclusions(str(r.get("name", "")), exclude_ingredients)
        ]
        return filtered
