"""gigs.sh adapter — 46-platform agent earning directory, use for discovery only."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter

log = logging.getLogger(__name__)

BASE = "https://www.gigs.sh"


class GigsAdapter(BaseAdapter):
    """gigs.sh is a directory, not a job board. We use it for platform discovery,
    not for direct earning. It lists 46 platforms — this adapter scrapes the
    directory to keep our platform registry current."""

    platform = Platform.GIGS

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE, timeout=30)

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        """gigs.sh doesn't have jobs — it has platform listings.
        This yields metadata about platforms, not actionable opportunities."""
        try:
            from selectolax.parser import HTMLParser
        except ImportError:
            return

        try:
            resp = await self.client.get("/")
            resp.raise_for_status()
            tree = HTMLParser(resp.text)
            cards = tree.css("article, [class*=card], [class*=platform], [class*=entry]")
            for card in cards:
                title_el = card.css_first("h2, h3, h4, a")
                desc_el = card.css_first("p, [class*=desc]")
                link_el = card.css_first("a[href]")
                title = title_el.text(strip=True) if title_el else ""
                desc = desc_el.text(strip=True) if desc_el else ""
                href = link_el.attributes.get("href", "") if link_el else ""
                if title:
                    yield Opportunity(
                        platform=Platform.GIGS,
                        title=title,
                        description=desc,
                        url=href if href.startswith("http") else f"{BASE}{href}",
                        category=TaskCategory.UNKNOWN,
                        reward=0,
                        verification_strength=0,
                        payment_reliability=0,
                    )
        except Exception as e:
            log.warning("gigs.sh scrape error: %s", e)

    async def claim(self, opportunity: Opportunity) -> bool:
        return False  # Discovery-only

    async def submit(self, opportunity: Opportunity, result: dict) -> bool:
        return False

    async def check_status(self, opportunity: Opportunity) -> dict:
        return {"status": "directory_entry"}

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get("/")
            return resp.status_code < 500
        except Exception:
            return False
