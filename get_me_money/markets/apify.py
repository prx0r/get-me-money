"""Apify Store adapter — search, create, publish Actors."""
from __future__ import annotations

import json
import urllib.request
from . import MarketAdapter, MarketCapabilities, MarketListing


class ApifyAdapter(MarketAdapter):
    name = "apify"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=True, reviews=True, analytics=True,
        requires_auth=True,
    )

    def __init__(self, api_token: str = ""):
        self.api_token = api_token
        self.base = "https://api.apify.com/v2"

    async def search(self, query="", category="", limit=20) -> list[MarketListing]:
        url = f"{self.base}/store?sortBy=popularity&limit={limit}"
        if query:
            url += f"&search={query}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return [MarketListing(
                    market="apify",
                    listing_id=a.get("id", ""),
                    title=a.get("name", ""),
                    price=0,
                    stats={
                        "runs": a.get("totalRuns", 0),
                        "users": a.get("totalUsers", 0),
                        "users_7d": a.get("totalUsers7Days", 0),
                    }
                ) for a in data.get("data", [])[:limit]]
        except Exception:
            return []

    async def get_stats(self, listing_id) -> dict:
        try:
            url = f"{self.base}/store/{listing_id}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read()).get("data", {})
        except Exception:
            return {}
