import abc
import logging
from typing import Any

from app.llm.tools.tool_interface import ITool
from app.llm.tools.search.searchers.searcher_interface import MarketplaceSearcher
from app.llm.tools.search.searchers.amazon_searcher import AmazonSearcher
from app.llm.tools.search.searchers.mercado_livre_searcher import MercadoLivreSearcher

logger = logging.getLogger(__name__)

class SearchTool(ITool):
    """LLM tool that searches for supplement products across marketplaces."""
    def __init__(self):
        _searchers: list[MarketplaceSearcher] = [
           MercadoLivreSearcher(),
           AmazonSearcher(),
        ]

    async def execute(self, params: dict[str, Any]) -> str:
        return {
            "name": "SearchTool",
            "price": 100,
            "url": "https://www.google.com",
            "source": "Google",
        }

    async def execute_new(self, params: dict[str, Any]) -> str:
        query = params.get("query", "")
        exclude_ingredients = params.get("exclude_ingredients", [])

        all_results: list[dict] = []
        for searcher in self._searchers:
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
