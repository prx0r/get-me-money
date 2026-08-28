"""TryBounty adapter — the best agent-native opportunity now."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter

log = logging.getLogger(__name__)

BASE = "https://trybounty.ai"


def _categorize(title: str, desc: str) -> TaskCategory:
    t = (title + " " + desc).lower()
    if any(w in t for w in ["code", "bug", "fix", "pr", "pull request", "repo"]):
        return TaskCategory.CODE_FIX
    if any(w in t for w in ["research", "list", "prospect", "data"]):
        return TaskCategory.RESEARCH
    if any(w in t for w in ["content", "article", "blog", "copy"]):
        return TaskCategory.CONTENT
    if any(w in t for w in ["api", "integration", "endpoint"]):
        return TaskCategory.API_WORK
    if any(w in t for w in ["test", "qa", "quality"]):
        return TaskCategory.TESTING
    if any(w in t for w in ["doc", "readme", "documentation"]):
        return TaskCategory.DOCUMENTATION
    return TaskCategory.UNKNOWN


class BountyAdapter(BaseAdapter):
    platform = Platform.BOUNTY

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=BASE,
            timeout=30,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        """Scrape / discover bounty listings."""
        try:
            # Try API first if we have a key
            if self.api_key:
                async for opp in self._discover_api(max_pages):
                    yield opp
                return

            # Fallback: scrape the HTML listing
            async for opp in self._discover_scrape(max_pages):
                yield opp
        except Exception as e:
            log.warning("Bounty discover error: %s", e)

    async def _discover_api(self, max_pages: int) -> AsyncIterator[Opportunity]:
        for page in range(1, max_pages + 1):
            resp = await self.client.get("/api/bounties", params={
                "page": page, "status": "open", "limit": 20
            })
            resp.raise_for_status()
            data = resp.json()
            items = data if isinstance(data, list) else data.get("bounties", [])
            if not items:
                break
            for item in items:
                yield self._to_opportunity(item)

    async def _discover_scrape(self, max_pages: int) -> AsyncIterator[Opportunity]:
        """Best-effort HTML scrape when no API key."""
        try:
            from selectolax.parser import HTMLParser
        except ImportError:
            log.warning("selectolax not installed, cannot scrape Bounty")
            return

        for page in range(1, max_pages + 1):
            try:
                resp = await self.client.get("/bounties", params={"page": page})
                resp.raise_for_status()
                tree = HTMLParser(resp.text)
                cards = tree.css("[class*=bounty], [class*=card], article")
                if not cards:
                    break
                for card in cards:
                    title_el = card.css_first("h2, h3, [class*=title]")
                    link_el = card.css_first("a[href]")
                    price_el = card.css_first("[class*=price], [class*=amount], [class*=reward]")
                    title = title_el.text(strip=True) if title_el else ""
                    href = link_el.attributes.get("href", "") if link_el else ""
                    price_text = price_el.text(strip=True) if price_el else ""
                    reward = _parse_reward(price_text)
                    if title:
                        yield Opportunity(
                            platform=Platform.BOUNTY,
                            title=title,
                            url=f"{BASE}{href}" if href.startswith("/") else href,
                            reward=reward,
                            category=_categorize(title, ""),
                            verification_strength=0.7,
                            payment_reliability=0.7,
                        )
            except Exception as e:
                log.debug("Bounty scrape page %d error: %s", page, e)
                break

    def _to_opportunity(self, data: dict) -> Opportunity:
        return Opportunity(
            platform=Platform.BOUNTY,
            external_id=str(data.get("id", "")),
            title=data.get("title", ""),
            description=data.get("description", ""),
            url=data.get("url", ""),
            reward=float(data.get("reward", data.get("amount", 0))),
            currency=data.get("currency", "USD"),
            category=_categorize(data.get("title", ""), data.get("description", "")),
            tags=data.get("tags", []),
            posted_at=data.get("posted_at", 0),
            competition_estimate=data.get("applicant_count", 0),
            verification_strength=0.7,
            payment_reliability=0.7,
            raw=data,
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        log.info("Bounty claim: %s", opportunity.title)
        if not self.api_key:
            log.warning("No Bounty API key — cannot auto-claim")
            return False
        try:
            resp = await self.client.post(f"/api/bounties/{opportunity.external_id}/apply")
            resp.raise_for_status()
            return True
        except Exception as e:
            log.warning("Bounty claim failed: %s", e)
            return False

    async def submit(self, opportunity: Opportunity, result: dict) -> bool:
        if not self.api_key:
            return False
        try:
            resp = await self.client.post(
                f"/api/bounties/{opportunity.external_id}/submit",
                json=result,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            log.warning("Bounty submit failed: %s", e)
            return False

    async def check_status(self, opportunity: Opportunity) -> dict:
        if not self.api_key:
            return {"status": "unknown"}
        try:
            resp = await self.client.get(f"/api/bounties/{opportunity.external_id}")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {"status": "unknown"}

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get("/")
            return resp.status_code < 500
        except Exception:
            return False


def _parse_reward(text: str) -> float:
    import re
    m = re.search(r"\$?([\d,]+\.?\d*)", text.replace(",", ""))
    if m:
        return float(m.group(1))
    return 0.0
