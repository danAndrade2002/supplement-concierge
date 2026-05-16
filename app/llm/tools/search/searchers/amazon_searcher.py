from app.llm.tools.search.searchers.searcher_interface import MarketplaceSearcher


class AmazonSearcher(MarketplaceSearcher):
    async def search(
        self, query: str, exclude_ingredients: list[str]
    ) -> list[dict]:
        raise NotImplementedError("Amazon integration not yet implemented")
