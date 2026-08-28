"""itch.io — butler uploads, game/asset publishing."""
from __future__ import annotations
from . import MarketAdapter, MarketCapabilities

class ItchioAdapter(MarketAdapter):
    name = "itchio"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=True, reviews=False, analytics=True,
        requires_auth=True,
    )
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
