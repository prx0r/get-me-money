"""Clustly adapter — agent-native marketplace, 4% fee, serious transparency."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter

log = logging.getLogger(__name__)

BASE = "https://www.clustly.ai"


def _categorize(title: str, desc: str) -> TaskCategory:
    t = (title + " " + desc).lower()
    if any(w in t for w in ["code", "bug", "fix", "script", "program"]):
        return TaskCategory.CODE_FIX
    if any(w in t for w in ["research", "data", "analysis", "report"]):
        return TaskCategory.RESEARCH
    if any(w in t for w in ["content", "write", "article", "copy"]):
        return TaskCategory.CONTENT
    if any(w in t for w in ["api", "integration", "automation"]):
        return TaskCategory.API_WORK
    if any(w in t for w in ["document", "readme", "doc"]):
        return TaskCategory.DOCUMENTATION
    return TaskCategory.UNKNOWN


class ClustlyAdapter(BaseAdapter):
    platform = Platform.CLUSTLY

    def __init__(self, token: str = ""):
        self.token = token
        self.client = httpx.AsyncClient(
            base_url=BASE,
            timeout=30,
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        try:
            # Try API
            for page in range(1, max_pages + 1):
                resp = await self.client.get("/api/tasks", params={
                    "page": page, "status": "open"
                })
                if resp.status_code >= 400:
                    break
                data = resp.json()
                items = data if isinstance(data, list) else data.get("tasks", [])
                if not items:
                    break
                for item in items:
                    yield self._to_opportunity(item)
        except Exception as e:
            log.debug("Clustly API error: %s, trying scrape", e)

        # HTML fallback
        try:
            async for opp in self._discover_scrape(max_pages):
                yield opp
        except Exception as e:
            log.warning("Clustly scrape error: %s", e)

    async def _discover_scrape(self, max_pages: int) -> AsyncIterator[Opportunity]:
        try:
            from selectolax.parser import HTMLParser
        except ImportError:
            return

        for page in range(1, max_pages + 1):
            try:
                resp = await self.client.get("/tasks", params={"page": page})
                if resp.status_code >= 400:
                    break
                tree = HTMLParser(resp.text)
                cards = tree.css("[class*=task], [class*=card], article")
                if not cards:
                    break
                for card in cards:
                    title_el = card.css_first("h2, h3, h4, [class*=title]")
                    link_el = card.css_first("a[href]")
                    price_el = card.css_first("[class*=price], [class*=reward], [class*=amount]")
                    title = title_el.text(strip=True) if title_el else ""
                    href = link_el.attributes.get("href", "") if link_el else ""
                    price_text = price_el.text(strip=True) if price_el else ""

                    import re
                    m = re.search(r"\$?([\d,.]+)", price_text.replace(",", ""))
                    reward = float(m.group(1)) if m else 0.0

                    if title:
                        yield Opportunity(
                            platform=Platform.CLUSTLY,
                            title=title,
                            url=f"{BASE}{href}" if href.startswith("/") else href,
                            reward=reward,
                            category=_categorize(title, ""),
                            verification_strength=0.7,
                            payment_reliability=0.6,
                        )
            except Exception as e:
                log.debug("Clustly scrape page %d: %s", page, e)
                break

    def _to_opportunity(self, data: dict) -> Opportunity:
        reward = 0.0
        for key in ("reward", "amount", "price", "payment"):
            if key in data:
                try:
                    reward = float(data[key])
                    break
                except (ValueError, TypeError):
                    pass

        return Opportunity(
            platform=Platform.CLUSTLY,
            external_id=str(data.get("id", "")),
            title=data.get("title", data.get("name", "")),
            description=data.get("description", ""),
            url=data.get("url", ""),
            reward=reward,
            currency=data.get("currency", "USD"),
            category=_categorize(data.get("title", ""), data.get("description", "")),
            tags=data.get("tags", []),
            posted_at=data.get("created_at", 0),
            competition_estimate=data.get("applicants", 0),
            verification_strength=0.7,
            payment_reliability=0.6,
            raw=data,
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        log.info("Clustly claim: %s", opportunity.title)
        if not self.token:
            return False
        try:
            resp = await self.client.post(f"/api/tasks/{opportunity.external_id}/claim")
            resp.raise_for_status()
            return True
        except Exception as e:
            log.warning("Clustly claim failed: %s", e)
            return False

    async def submit(self, opportunity: Opportunity, result: dict) -> bool:
        if not self.token:
            return False
        try:
            resp = await self.client.post(
                f"/api/tasks/{opportunity.external_id}/submit",
                json=result,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            log.warning("Clustly submit failed: %s", e)
            return False

    async def check_status(self, opportunity: Opportunity) -> dict:
        try:
            resp = await self.client.get(f"/api/tasks/{opportunity.external_id}")
            if resp.status_code < 400:
                return resp.json()
        except Exception:
            pass
        return {"status": "unknown"}
