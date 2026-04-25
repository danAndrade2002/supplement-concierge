from app.llm.tools.search.searchers.searcher_interface import MarketplaceSearcher


class MercadoLivreSearcher(MarketplaceSearcher):
    async def search(
        self, query: str, exclude_ingredients: list[str]
    ) -> list[dict]:
        raise NotImplementedError("Mercado Livre integration not yet implemented")

