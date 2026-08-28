"""Superteam Earn adapter — $500-$5k bounties, agent API exists."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter

log = logging.getLogger(__name__)

BASE = "https://earn.superteam.io"


class SuperteamAdapter(BaseAdapter):
    platform = Platform.SUPERTEAM

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=BASE,
            timeout=30,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        try:
            for page in range(1, max_pages + 1):
                resp = await self.client.get("/api/bounties", params={
                    "page": page, "status": "open"
                })
                if resp.status_code >= 400:
                    break
                data = resp.json()
                items = data if isinstance(data, list) else data.get("bounties", [])
                if not items:
                    break
                for item in items:
                    # Skip bounties that don't allow AI entries
                    if not item.get("agent_eligible", True):
                        log.debug("Skipping non-agent-eligible bounty: %s", item.get("title"))
                        continue
                    yield self._to_opportunity(item)
        except Exception as e:
            log.warning("Superteam discover error: %s", e)

    def _to_opportunity(self, data: dict) -> Opportunity:
        reward = 0.0
        for key in ("reward", "amount", "prize_pool", "total_reward"):
            if key in data:
                try:
                    reward = float(data[key])
                    break
                except (ValueError, TypeError):
                    pass

        tags = data.get("tags", [])
        cat = TaskCategory.RESEARCH
        t = " ".join(tags + [data.get("title", "")]).lower()
        if any(w in t for w in ["code", "dev", "engineering", "hack"]):
            cat = TaskCategory.CODE_FIX
        elif any(w in t for w in ["design", "ui", "ux"]):
            cat = TaskCategory.DESIGN

        return Opportunity(
            platform=Platform.SUPERTEAM,
            external_id=str(data.get("id", "")),
            title=data.get("title", ""),
            description=data.get("description", data.get("body", "")),
            url=data.get("url", data.get("apply_url", "")),
            reward=reward,
            currency=data.get("currency", "USD"),
            category=cat,
            tags=tags,
            posted_at=data.get("created_at", 0),
            competition_estimate=data.get("submissions_count", 0),
            verification_strength=0.8,
            payment_reliability=0.8,
            raw=data,
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        log.info("Superteam claim: %s", opportunity.title)
        return True

    async def submit(self, opportunity: Opportunity, result: dict) -> bool:
        if not self.api_key:
            log.warning("No Superteam API key")
            return False
        try:
            resp = await self.client.post(
                f"/api/bounties/{opportunity.external_id}/submit",
                json=result,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            log.warning("Superteam submit failed: %s", e)
            return False

    async def check_status(self, opportunity: Opportunity) -> dict:
        try:
            resp = await self.client.get(f"/api/bounties/{opportunity.external_id}")
            if resp.status_code < 400:
                return resp.json()
        except Exception:
            pass
        return {"status": "unknown"}
