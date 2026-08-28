"""Algora adapter — GitHub bounties, serious money ($50-$2500)."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter

log = logging.getLogger(__name__)

BASE = "https://algora.io"


class AlgoraAdapter(BaseAdapter):
    platform = Platform.ALGORA

    def __init__(self, token: str = ""):
        self.token = token
        self.client = httpx.AsyncClient(
            base_url=BASE,
            timeout=30,
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        try:
            async for opp in self._discover_api(max_pages):
                yield opp
        except Exception as e:
            log.warning("Algora discover error: %s", e)
            # Fallback to HTML scrape
            try:
                async for opp in self._discover_scrape(max_pages):
                    yield opp
            except Exception as e2:
                log.warning("Algora scrape fallback error: %s", e2)

    async def _discover_api(self, max_pages: int) -> AsyncIterator[Opportunity]:
        for page in range(1, max_pages + 1):
            resp = await self.client.get("/api/bounties", params={
                "page": page, "status": "open"
            })
            if resp.status_code == 404:
                # Try alternate endpoint
                resp = await self.client.get("/api/v1/bounties", params={
                    "page": page, "status": "open"
                })
            if resp.status_code >= 400:
                log.debug("Algora API returned %d, falling back to scrape", resp.status_code)
                break
            data = resp.json()
            items = data if isinstance(data, list) else data.get("bounties", [])
            if not items:
                break
            for item in items:
                yield self._to_opportunity(item)

    async def _discover_scrape(self, max_pages: int) -> AsyncIterator[Opportunity]:
        try:
            from selectolax.parser import HTMLParser
        except ImportError:
            return

        for page in range(1, max_pages + 1):
            try:
                resp = await self.client.get("/bounties", params={"page": page})
                resp.raise_for_status()
                tree = HTMLParser(resp.text)
                cards = tree.css("[class*=bounty], [class*=card], tr, article")
                if not cards:
                    break
                for card in cards:
                    title_el = card.css_first("h2, h3, h4, [class*=title], [class*=name]")
                    link_el = card.css_first("a[href*='bounty'], a[href*='issue']")
                    price_el = card.css_first("[class*=reward], [class*=amount], [class*=price]")
                    title = title_el.text(strip=True) if title_el else ""
                    href = link_el.attributes.get("href", "") if link_el else ""
                    price_text = price_el.text(strip=True) if price_el else ""
                    import re
                    m = re.search(r"\$?([\d,]+)", price_text.replace(",", ""))
                    reward = float(m.group(1)) if m else 0.0
                    if title:
                        yield Opportunity(
                            platform=Platform.ALGORA,
                            title=title,
                            url=f"{BASE}{href}" if href.startswith("/") else href,
                            reward=reward,
                            category=TaskCategory.CODE_FIX,
                            verification_strength=0.9,  # GitHub PR merge = strong verification
                            payment_reliability=0.8,
                        )
            except Exception as e:
                log.debug("Algora scrape page %d: %s", page, e)
                break

    def _to_opportunity(self, data: dict) -> Opportunity:
        reward = 0.0
        if "reward" in data:
            reward = float(data["reward"]) if isinstance(data["reward"], (int, float, str)) else 0
        elif "amount" in data:
            reward = float(data["amount"])
        elif "bounty_amount" in data:
            reward = float(data["bounty_amount"])

        return Opportunity(
            platform=Platform.ALGORA,
            external_id=str(data.get("id", data.get("number", ""))),
            title=data.get("title", data.get("name", "")),
            description=data.get("description", data.get("body", "")),
            url=data.get("html_url", data.get("url", "")),
            reward=reward,
            currency=data.get("currency", "USD"),
            category=TaskCategory.CODE_FIX,
            tags=data.get("labels", []),
            posted_at=data.get("created_at", 0),
            competition_estimate=data.get("comments_count", 0),
            verification_strength=0.9,
            payment_reliability=0.8,
            raw=data,
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        log.info("Algora claim (open issue): %s", opportunity.title)
        # Algora doesn't have explicit claim — you open a PR
        # This is a no-op; the executor handles the actual work
        return True

    async def submit(self, opportunity: Opportunity, result: dict) -> bool:
        # Submission is via GitHub PR, not via Algora API
        log.info("Algora submit: PR URL = %s", result.get("pr_url", ""))
        return True

    async def check_status(self, opportunity: Opportunity) -> dict:
        try:
            resp = await self.client.get(f"/api/bounties/{opportunity.external_id}")
            if resp.status_code == 404:
                resp = await self.client.get(f"/api/v1/bounties/{opportunity.external_id}")
            if resp.status_code < 400:
                return resp.json()
        except Exception:
            pass
        return {"status": "unknown"}

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get("/bounties")
            return resp.status_code < 500
        except Exception:
            return False
