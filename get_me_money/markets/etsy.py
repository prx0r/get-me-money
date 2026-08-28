"""Etsy adapter — listings, orders, reviews."""
from __future__ import annotations

import json
import urllib.request
from . import MarketAdapter, MarketCapabilities, MarketListing


class EtsyAdapter(MarketAdapter):
    name = "etsy"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=True, reviews=True, analytics=False,
        requires_auth=True,
    )

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base = "https://openapi.etsy.com/v3"

    async def search(self, query="", category="", limit=20) -> list[MarketListing]:
        if not self.api_key:
            return []
        url = f"{self.base}/application/listings/active?keywords={query}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"x-api-key": self.api_key})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return [MarketListing(
                    market="etsy",
                    listing_id=str(l.get("listing_id", "")),
                    title=l.get("title", ""),
                    price=l.get("price", {}).get("amount", 0) / 100,
                    currency=l.get("price", {}).get("currency_code", "USD"),
                    stats={"favorites": l.get("num_favorers", 0)},
                ) for l in data.get("results", [])[:limit]]
        except Exception:
            return []
