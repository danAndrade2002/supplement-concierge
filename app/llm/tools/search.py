import abc
import logging
from typing import Any

from app.llm.tools.tool_interface import ITool

logger = logging.getLogger(__name__)


class MarketplaceSearcher(abc.ABC):
    """Interface for marketplace product search."""

    @abc.abstractmethod
    async def search(
        self, query: str, exclude_ingredients: list[str]
    ) -> list[dict]:
        """Returns a list of dicts with keys: name, price, url, source."""
        ...


class MercadoLivreSearcher(MarketplaceSearcher):
    async def search(
        self, query: str, exclude_ingredients: list[str]
    ) -> list[dict]:
        raise NotImplementedError("Mercado Livre integration not yet implemented")


class AmazonSearcher(MarketplaceSearcher):
    async def search(
        self, query: str, exclude_ingredients: list[str]
    ) -> list[dict]:
        raise NotImplementedError("Amazon integration not yet implemented")


_searchers: list[MarketplaceSearcher] = [
    MercadoLivreSearcher(),
    AmazonSearcher(),
]


class SearchTool(ITool):
    """LLM tool that searches for supplement products across marketplaces."""

    async def execute(self, params: dict[str, Any]) -> str:
        query = params.get("query", "")
        exclude_ingredients = params.get("exclude_ingredients", [])

        all_results: list[dict] = []
        for searcher in _searchers:
            try:
                results = await searcher.search(query, exclude_ingredients)
                all_results.extend(results)
            except NotImplementedError:
                logger.debug("Skipping %s (not implemented)", searcher.__class__.__name__)

        if not all_results:
            return "No products found. The marketplace integrations are not yet configured."

        all_results.sort(key=lambda r: r.get("price", float("inf")))
        top = all_results[:3]

        lines = []
        for i, r in enumerate(top, 1):
            lines.append(f"{i}. {r['name']} - ${r['price']:.2f} ({r['source']})\n   {r['url']}")
        return "\n".join(lines)
