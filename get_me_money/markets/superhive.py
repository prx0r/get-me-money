"""Superhive adapter — Blender asset marketplace."""
from __future__ import annotations

import json
import urllib.request
from . import MarketAdapter, MarketCapabilities, MarketListing


class SuperhiveAdapter(MarketAdapter):
    name = "superhive"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=True, reviews=True, analytics=False,
        requires_auth=True,
    )

    def __init__(self, auth_token: str = ""):
        self.auth_token = auth_token
        self.base = "https://superhivemarket.com/api"

    async def search(self, query="", category="", limit=20) -> list[MarketListing]:
        try:
            url = f"{self.base}/assets/search?q={query}&limit={limit}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return [MarketListing(
                    market="superhive",
                    listing_id=a.get("id", ""),
                    title=a.get("title", ""),
                    price=a.get("price", 0),
                ) for a in data.get("assets", [])[:limit]]
        except Exception:
            return []
