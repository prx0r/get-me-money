"""Market adapters — unified interface for publishing to marketplaces."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class MarketCapabilities:
    discover: bool = False
    create: bool = False
    upload: bool = False
    publish: bool = False
    sales: bool = False
    reviews: bool = False
    analytics: bool = False
    requires_auth: bool = True
    requires_human: bool = False


@dataclass
class MarketListing:
    market: str = ""
    listing_id: str = ""
    title: str = ""
    price: float = 0.0
    currency: str = "USD"
    status: str = ""
    url: str = ""
    stats: dict = field(default_factory=dict)


class MarketAdapter:
    name: str = ""
    capabilities: MarketCapabilities = MarketCapabilities()

    async def search(self, query: str = "", category: str = "", limit: int = 20) -> list[MarketListing]:
        return []

    async def get_stats(self, listing_id: str) -> dict:
        return {}

    async def create_draft(self, title: str, description: str, price: float, **kwargs) -> MarketListing:
        raise NotImplementedError

    async def upload(self, listing_id: str, artifact_path: str) -> bool:
        raise NotImplementedError

    async def publish(self, listing_id: str) -> bool:
        raise NotImplementedError

    async def get_sales(self, limit: int = 50) -> list[dict]:
        return []

    def can_operate_autonomously(self) -> bool:
        return (self.capabilities.discover and self.capabilities.create and
                self.capabilities.upload and self.capabilities.publish and
                not self.capabilities.requires_human)


# Registry
from get_me_money.markets.apify import ApifyAdapter
from get_me_money.markets.etsy import EtsyAdapter
from get_me_money.markets.roblox import RobloxAdapter
from get_me_money.markets.superhive import SuperhiveAdapter
from get_me_money.markets.webflow import WebflowAdapter

MARKET_ADAPTERS = {
    "apify": ApifyAdapter,
    "etsy": EtsyAdapter,
    "roblox": RobloxAdapter,
    "superhive": SuperhiveAdapter,
    "webflow": WebflowAdapter,
}


def get_adapter(market: str, **kwargs) -> MarketAdapter:
    cls = MARKET_ADAPTERS.get(market)
    if cls:
        return cls(**kwargs)
    return MarketAdapter()


def list_markets() -> list[dict]:
    return [
        {"name": k, "discover": v().capabilities.discover,
         "create": v().capabilities.create, "publish": v().capabilities.publish}
        for k, v in MARKET_ADAPTERS.items()
    ]
