"""Opire adapter — ~210 open bounties, ~$55k total."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter

log = logging.getLogger(__name__)

BASE = "https://opire.ai"


class OpireAdapter(BaseAdapter):
    platform = Platform.OPIRE

    def __init__(self, token: str = ""):
        self.token = token
        self.client = httpx.AsyncClient(
            base_url=BASE,
            timeout=30,
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        try:
            for page in range(1, max_pages + 1):
                resp = await self.client.get("/api/bounties", params={
                    "page": page, "status": "open", "limit": 20
                })
                if resp.status_code >= 400:
                    break
                data = resp.json()
                items = data if isinstance(data, list) else data.get("bounties", [])
                if not items:
                    break
                for item in items:
                    yield self._to_opportunity(item)
        except Exception as e:
            log.warning("Opire discover error: %s", e)

    def _to_opportunity(self, data: dict) -> Opportunity:
        reward = 0.0
        for key in ("reward", "amount", "bounty_amount", "value"):
            if key in data:
                try:
                    reward = float(data[key])
                    break
                except (ValueError, TypeError):
                    pass

        return Opportunity(
            platform=Platform.OPIRE,
            external_id=str(data.get("id", "")),
            title=data.get("title", ""),
            description=data.get("description", data.get("body", "")),
            url=data.get("html_url", data.get("url", "")),
            reward=reward,
            currency=data.get("currency", "USD"),
            category=TaskCategory.CODE_FIX if data.get("repo_url") else TaskCategory.RESEARCH,
            tags=data.get("tags", []),
            posted_at=data.get("created_at", 0),
            competition_estimate=data.get("comments_count", 0),
            verification_strength=0.8,
            payment_reliability=0.7,
            raw=data,
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        log.info("Opire claim: %s", opportunity.title)
        return True  # Claim is implicit via PR

    async def submit(self, opportunity: Opportunity, result: dict) -> bool:
        log.info("Opire submit: %s", result.get("pr_url", ""))
        return True

    async def check_status(self, opportunity: Opportunity) -> dict:
        try:
            resp = await self.client.get(f"/api/bounties/{opportunity.external_id}")
            if resp.status_code < 400:
                return resp.json()
        except Exception:
            pass
        return {"status": "unknown"}
