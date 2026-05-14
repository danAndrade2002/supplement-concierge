"""
Test the Mercado Livre search.
Requires MELI_ACCESS_TOKEN in .env — run auth_meli.py first if not set.

Usage:
  python test_meli.py                        # default queries
  python test_meli.py "whey protein"         # custom query
  python test_meli.py "whey" "creatina"      # multiple queries
"""
import asyncio
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent / ".env")

CLIENT_ID = os.getenv("MELI_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MELI_CLIENT_SECRET", "")
ACCESS_TOKEN = os.getenv("MELI_ACCESS_TOKEN", "")
REFRESH_TOKEN = os.getenv("MELI_REFRESH_TOKEN", "")
SITE_ID = os.getenv("MELI_SITE_ID", "MLB")

TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
PRODUCTS_URL = f"https://api.mercadolibre.com/products/search"
ITEMS_URL = "https://api.mercadolibre.com/products/{product_id}/items"
CATALOG_URL = "https://www.mercadolivre.com.br/p/{product_id}"


async def get_token(client: httpx.AsyncClient) -> str:
    if ACCESS_TOKEN:
        print(f"Token: {ACCESS_TOKEN[:20]}...\n")
        return ACCESS_TOKEN
    if REFRESH_TOKEN:
        print("Refreshing token...")
        r = await client.post(TOKEN_URL, data={
            "grant_type": "refresh_token", "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET, "refresh_token": REFRESH_TOKEN,
        }, headers={"content-type": "application/x-www-form-urlencoded"})
        r.raise_for_status()
        token = r.json()["access_token"]
        print(f"Refreshed: {token[:20]}...\n")
        return token
    print("ERROR: No MELI_ACCESS_TOKEN in .env. Run: python auth_meli.py\n")
    sys.exit(1)


async def fetch_min_price(client: httpx.AsyncClient, product_id: str, headers: dict) -> float | None:
    url = ITEMS_URL.format(product_id=product_id)
    r = await client.get(url, params={"status": "active", "limit": 5}, headers=headers)
    if r.status_code != 200:
        return None
    items = r.json().get("results", [])
    prices = [item["price"] for item in items if item.get("price") is not None]
    return float(min(prices)) if prices else None


async def search(client: httpx.AsyncClient, token: str, query: str, limit: int = 5) -> None:
    print(f"Searching: '{query}'\n{'-' * 40}")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(PRODUCTS_URL, params={"site_id": SITE_ID, "q": query, "limit": limit}, headers=headers)
    if r.status_code == 401:
        print("ERROR: Token expired. Run auth_meli.py to re-authenticate.\n")
        return
    r.raise_for_status()

    products = r.json().get("results", [])
    if not products:
        print("No results found.\n")
        return

    # Parallel fetch prices
    prices = await asyncio.gather(*[fetch_min_price(client, p["id"], headers) for p in products])

    for product, price in zip(products, prices):
        price_str = f"R$ {price:.2f}" if price is not None else "N/A"
        print(f"• {product['name']}")
        print(f"  Price: {price_str}")
        print(f"  URL:   {CATALOG_URL.format(product_id=product['id'])}")
        print()


async def main() -> None:
    queries = sys.argv[1:] or ["whey protein", "creatina monohidratada", "vitamina c"]
    async with httpx.AsyncClient(timeout=15.0) as client:
        token = await get_token(client)
        for query in queries:
            await search(client, token, query)


if __name__ == "__main__":
    asyncio.run(main())
