"""Publisher — upload artifacts to marketplaces via adapters.

Uses MarketAdapter protocol to publish to multiple venues.
Each adapter declares what it can do.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from get_me_money.markets import get_adapter, list_markets, MarketAdapter

log = logging.getLogger(__name__)


@dataclass
class PublishResult:
    venue: str = ""
    success: bool = False
    url: str = ""
    id: str = ""
    error: str = ""


class Publisher:
    """Publish artifacts to multiple marketplaces."""

    def __init__(self, config=None):
        self.config = config

    async def publish(
        self,
        title: str,
        content: str,
        artifacts: list[str] | None = None,
        price: float = 0.0,
        category: str = "report",
        venues: list[str] | None = None,
    ) -> list[PublishResult]:
        """Publish to one or more venues."""
        results = []

        for venue in (venues or ["apify"]):
            adapter = get_adapter(venue)
            if not adapter.name:
                results.append(PublishResult(venue=venue, error=f"Unknown venue: {venue}"))
                continue

            if not adapter.capabilities.create:
                results.append(PublishResult(
                    venue=venue,
                    error=f"Cannot create listings (capabilities: {adapter.capabilities})",
                ))
                continue

            try:
                listing = await adapter.create_draft(title, content, price)
                results.append(PublishResult(
                    venue=venue, success=True,
                    id=listing.listing_id, url=listing.url,
                ))
            except NotImplementedError:
                results.append(PublishResult(
                    venue=venue, error="Adapter not fully implemented",
                ))
            except Exception as e:
                results.append(PublishResult(venue=venue, error=str(e)))

        return results

    def list_available(self) -> list[dict]:
        """List all available markets and their capabilities."""
        return list_markets()
