"""Apple App Store — versions, metadata, TestFlight, reviews."""
from __future__ import annotations
from . import MarketAdapter, MarketCapabilities

class AppleAdapter(MarketAdapter):
    name = "apple"
    capabilities = MarketCapabilities(
        discover=True, create=True, upload=True, publish=True,
        sales=True, reviews=True, analytics=True,
        requires_auth=True,
    )
    def __init__(self, key_id: str = "", issuer: str = "", key_path: str = ""):
        self.key_id = key_id
        self.issuer = issuer
        self.key_path = key_path
