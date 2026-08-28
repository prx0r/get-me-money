"""Webflow adapter — site/template production via MCP."""
from __future__ import annotations

import json
import urllib.request
from . import MarketAdapter, MarketCapabilities, MarketListing


class WebflowAdapter(MarketAdapter):
    name = "webflow"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=False, reviews=False, analytics=True,
        requires_auth=True,
    )

    def __init__(self, api_token: str = ""):
        self.api_token = api_token
        self.base = "https://api.webflow.com/v2"

    async def search(self, query="", category="", limit=20) -> list[MarketListing]:
        # Webflow marketplace search — limited public API
        return []
