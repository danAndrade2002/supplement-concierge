import abc


class MarketplaceSearcher(abc.ABC): 
    """Interface for marketplace product search."""

    @abc.abstractmethod
    async def search(
        self, query: str, exclude_ingredients: list[str]
    ) -> list[dict]:
        """Returns a list of dicts with keys: name, price, url, source."""
        ...