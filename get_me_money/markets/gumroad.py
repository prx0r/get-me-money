"""Gumroad — products, memberships, license keys."""
from __future__ import annotations
from . import MarketAdapter, MarketCapabilities

class GumroadAdapter(MarketAdapter):
    name = "gumroad"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=True, reviews=False, analytics=True,
        requires_auth=True,
    )
    def __init__(self, access_token: str = ""):
        self.access_token = access_token
