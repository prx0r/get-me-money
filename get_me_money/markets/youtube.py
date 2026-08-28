"""YouTube — upload, metadata, analytics."""
from __future__ import annotations
from . import MarketAdapter, MarketCapabilities

class YouTubeAdapter(MarketAdapter):
    name = "youtube"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=True, reviews=False, analytics=True,
        requires_auth=True, requires_human=True,  # API compliance review
    )
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
