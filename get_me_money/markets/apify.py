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

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_token:
            h["Authorization"] = f"Bearer {self.api_token}"
        return h

    async def search(self, query="", category="", limit=20) -> list[MarketListing]:
        import urllib.parse
        url = f"{self.base}/store?limit={limit}"
        if query:
            url += f"&search={urllib.parse.quote(query)}"
        try:
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read())
                items = raw.get("data", {}).get("items", [])
                return [MarketListing(
                    market="apify",
                    listing_id=a.get("username", "") + "/" + a.get("name", ""),
                    title=a.get("title", ""),
                    price=0,
                    stats={
                        "runs": a.get("stats", {}).get("totalRuns", 0),
                        "users": a.get("stats", {}).get("totalUsers", 0),
                        "users_7d": a.get("stats", {}).get("totalUsers7D", 0),
                        "category": a.get("category", ""),
                    }
                ) for a in items[:limit]]
        except Exception as e:
            print(f"Apify search error: {e}")
            return []

    async def get_stats(self, listing_id) -> dict:
        try:
            url = f"{self.base}/store/{listing_id}"
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read())
                return raw.get("data", {})
        except Exception:
            return {}

    async def create_draft(self, title, description, price=0, **kwargs) -> MarketListing:
        if not self.api_token:
            raise ValueError("API token required to create Actors")
        data = json.dumps({
            "name": title.lower().replace(" ", "-"),
            "description": description,
            "isPublic": True,
        }).encode()
        req = urllib.request.Request(
            f"{self.base}/acts",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            actor = result.get("data", {})
            return MarketListing(
                market="apify",
                listing_id=actor.get("username", "") + "/" + actor.get("name", ""),
                title=actor.get("name", ""),
                url=f"https://apify.com/{actor.get('username', '')}/{actor.get('name', '')}",
            )
