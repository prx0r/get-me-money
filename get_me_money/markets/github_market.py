"""GitHub Marketplace — apps, pricing plans, subscriptions."""
from __future__ import annotations
from . import MarketAdapter, MarketCapabilities

class GitHubMarketAdapter(MarketAdapter):
    name = "github_market"
    capabilities = MarketCapabilities(
        discover=True, create=False, upload=False, publish=False,
        sales=True, reviews=False, analytics=True,
        requires_auth=True, requires_human=True,  # listing needs verification
    )
    def __init__(self, token: str = ""):
        self.token = token
