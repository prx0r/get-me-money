"""Apify Store adapter — search, create, publish Actors.

Full API: https://docs.apify.com/api/v2/store
Actor management: https://docs.apify.com/api/v2/actors
"""
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
        url = f"{self.base}/store?sortBy=popularity&limit={limit}"
        if query:
            url += f"&search={query}"
        try:
            req = urllib.request.Request(url, headers=self._headers())
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
                        "category": a.get("category", ""),
                    }
                ) for a in data.get("data", [])[:limit]]
        except Exception:
            return []

    async def get_stats(self, listing_id) -> dict:
        try:
            url = f"{self.base}/store/{listing_id}"
            req = urllib.request.Request(url, headers=self._headers())
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read()).get("data", {})
        except Exception:
            return {}

    async def create_draft(self, title, description, price=0, **kwargs) -> MarketListing:
        if not self.api_token:
            raise ValueError("API token required to create Actors")
        # Create Actor via API
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
                listing_id=actor.get("id", ""),
                title=actor.get("name", ""),
                url=f"https://apify.com/{actor.get('username', '')}/{actor.get('name', '')}",
            )
