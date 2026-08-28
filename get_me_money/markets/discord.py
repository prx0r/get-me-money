"""Discord Apps — subscriptions, purchases, entitlements."""
from __future__ import annotations
from . import MarketAdapter, MarketCapabilities

class DiscordAdapter(MarketAdapter):
    name = "discord"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=False, publish=False,
        sales=True, reviews=False, analytics=True,
        requires_auth=True, requires_human=True,  # publish needs review
    )
    def __init__(self, token: str = ""):
        self.token = token
