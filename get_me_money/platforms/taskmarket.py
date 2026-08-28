"""Taskmarket adapter — cleanest agent earning implementation.

ERC-8004 agent identity, USDC payments, 7.5% fee.
CLI: taskmarket init → taskmarket task list → submit.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter

log = logging.getLogger(__name__)

BASE = "https://api.taskmarket.dev"
DOCS_BASE = "https://docs.taskmarket.dev"


def _categorize(title: str, desc: str) -> TaskCategory:
    t = (title + " " + desc).lower()
    if any(w in t for w in ["code", "build", "fix", "bug", "repo", "pr"]):
        return TaskCategory.CODE_FIX
    if any(w in t for w in ["research", "data", "analysis", "index", "discovery"]):
        return TaskCategory.RESEARCH
    if any(w in t for w in ["design", "ui", "ux", "figma"]):
        return TaskCategory.DESIGN
    if any(w in t for w in ["content", "write", "article", "blog"]):
        return TaskCategory.CONTENT
    if any(w in t for w in ["api", "integration", "x402", "agent"]):
        return TaskCategory.API_WORK
    return TaskCategory.UNKNOWN


class TaskmarketAdapter(BaseAdapter):
    platform = Platform.TASKMARKET

    def __init__(self, api_key: str = "", wallet_address: str = ""):
        self.api_key = api_key
        self.wallet_address = wallet_address
        self.client = httpx.AsyncClient(
            base_url=BASE,
            timeout=30,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            } if api_key else {},
        )

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        """Fetch open funded tasks from Taskmarket."""
        try:
            # Try the API endpoint
            resp = await self.client.get("/tasks", params={
                "status": "open",
                "limit": 20,
            })
            if resp.status_code >= 400:
                # Try alternate endpoint
                resp = await self.client.get("/api/tasks", params={
                    "status": "open",
                })
            if resp.status_code >= 400:
                log.debug("Taskmarket API %d, trying docs scrape", resp.status_code)
                async for opp in self._discover_scrape(max_pages):
                    yield opp
                return

            data = resp.json()
            items = data if isinstance(data, list) else data.get("tasks", [])
            for item in items:
                yield self._to_opportunity(item)
        except Exception as e:
            log.warning("Taskmarket discover error: %s", e)

    async def _discover_scrape(self, max_pages: int) -> AsyncIterator[Opportunity]:
        """Best-effort scrape from docs/task pages."""
        try:
            from selectolax.parser import HTMLParser
        except ImportError:
            return

        try:
            resp = await httpx.AsyncClient(timeout=30).get(
                "https://taskmarket.dev/", follow_redirects=True
            )
            if resp.status_code >= 400:
                return
            tree = HTMLParser(resp.text)
            # Look for task cards/listings
            cards = tree.css("[class*=task], [class*=card], [class*=bounty], article, tr")
            for card in cards:
                title_el = card.css_first("h2, h3, h4, [class*=title], a")
                price_el = card.css_first("[class*=reward], [class*=amount], [class*=price], [class*=usdc]")
                title = title_el.text(strip=True) if title_el else ""
                price_text = price_el.text(strip=True) if price_el else ""

                import re
                m = re.search(r"(\d+\.?\d*)\s*(?:USDC|usdc|\$)", price_text)
                reward = float(m.group(1)) if m else 0.0
                if not reward:
                    m2 = re.search(r"\$?([\d,.]+)", price_text)
                    reward = float(m2.group(1).replace(",", "")) if m2 else 0.0

                if title and reward > 0:
                    yield Opportunity(
                        platform=Platform.TASKMARKET,
                        title=title,
                        reward=reward,
                        currency="USDC",
                        category=_categorize(title, ""),
                        verification_strength=0.8,
                        payment_reliability=0.7,
                    )
        except Exception as e:
            log.debug("Taskmarket scrape error: %s", e)

    def _to_opportunity(self, data: dict) -> Opportunity:
        # Taskmarket rewards are in 6-decimal USDC units (1 USDC = 1e6 units)
        # Prefer netReward (after platform fee) if available
        reward = 0.0
        raw_reward = 0.0
        for key in ("reward", "amount", "payment", "usdc_amount", "value"):
            if key in data:
                try:
                    raw_reward = float(data[key])
                    break
                except (ValueError, TypeError):
                    pass

        if "netReward" in data:
            try:
                reward = float(data["netReward"]) / 1_000_000
            except (ValueError, TypeError):
                pass
        elif raw_reward:
            reward = raw_reward / 1_000_000

        submission_count = 0
        for key in ("submissions", "submission_count", "entries"):
            if key in data:
                try:
                    submission_count = int(data[key])
                    break
                except (ValueError, TypeError):
                    pass
        if not submission_count and "submissionCount" in data:
            try:
                submission_count = int(data["submissionCount"])
            except (ValueError, TypeError):
                pass

        # Title may be absent; extract first line from description
        title = data.get("title", data.get("name", ""))
        description = data.get("description", data.get("body", ""))
        if not title and description:
            title = description.split("\n")[0][:80]

        return Opportunity(
            platform=Platform.TASKMARKET,
            external_id=str(data.get("id", data.get("task_id", ""))),
            title=title,
            description=description,
            url=data.get("url", data.get("html_url", "")),
            reward=reward,
            currency="USDC",
            category=_categorize(title, description),
            tags=data.get("tags", []),
            posted_at=data.get("created_at", data.get("posted_at", 0)),
            competition_estimate=submission_count,
            verification_strength=0.8,
            payment_reliability=0.7,
            raw=data,
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        """Taskmarket doesn't require explicit claim — submit directly."""
        log.info("Taskmarket claim (no-op): %s", opportunity.title)
        return True

    async def submit(self, opportunity: Opportunity, result: dict) -> bool:
        """Submit work to Taskmarket."""
        if not self.api_key:
            log.warning("No Taskmarket API key — cannot submit")
            return False
        try:
            resp = await self.client.post(
                f"/tasks/{opportunity.external_id}/submit",
                json={
                    "content": result.get("content", ""),
                    "url": result.get("url", ""),
                    "metadata": result.get("metadata", {}),
                },
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            log.warning("Taskmarket submit failed: %s", e)
            return False

    async def check_status(self, opportunity: Opportunity) -> dict:
        try:
            resp = await self.client.get(f"/tasks/{opportunity.external_id}")
            if resp.status_code < 400:
                return resp.json()
        except Exception:
            pass
        return {"status": "unknown"}

    async def health_check(self) -> bool:
        try:
            resp = await httpx.AsyncClient(timeout=10).get("https://taskmarket.dev/")
            return resp.status_code < 500
        except Exception:
            return False
