"""Google Play — App Bundles, store listings, subscriptions."""
from __future__ import annotations
from . import MarketAdapter, MarketCapabilities

class GooglePlayAdapter(MarketAdapter):
    name = "google_play"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=True, reviews=True, analytics=True,
        requires_auth=True,
    )
    def __init__(self, service_account: str = ""):
        self.service_account = service_account
