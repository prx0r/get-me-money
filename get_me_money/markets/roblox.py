"""Roblox Creator Store adapter — search assets, create products."""
from __future__ import annotations

import json
import urllib.request
from . import MarketAdapter, MarketCapabilities, MarketListing


class RobloxAdapter(MarketAdapter):
    name = "roblox"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=False, reviews=False, analytics=False,
        requires_auth=True,
    )

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base = "https://apis.roblox.com/creator-store"

    async def search(self, query="", category="", limit=20) -> list[MarketListing]:
        # Public search doesn't require auth
        try:
            url = f"https://catalog.roblox.com/v1/search/items?keyword={query}&limit={limit}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return [MarketListing(
                    market="roblox",
                    listing_id=str(item.get("id", "")),
                    title=item.get("name", ""),
                    stats={"itemType": item.get("itemType", "")}
                ) for item in data.get("data", [])[:limit]]
        except Exception:
            return []
