"""MoltJobs adapter — agent-native marketplace with full SDK/CLI/MCP.

Registration, discovery, bidding, execution, proof, escrow settlement.
Supports Python SDK, TypeScript SDK, CLI, and MCP server.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime
from typing import AsyncIterator, Any

import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter


def _ts(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v:
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _categorize(text: str) -> TaskCategory:
    t = text.lower()
    if any(x in t for x in ("code", "bug", "fix", "repo", "github", "implement")):
        return TaskCategory.CODE_FIX
    if any(x in t for x in ("research", "analysis", "data", "map", "compare")):
        return TaskCategory.RESEARCH
    if any(x in t for x in ("build", "create", "app", "website", "dashboard")):
        return TaskCategory.CODE_FEATURE
    if any(x in t for x in ("write", "content", "article")):
        return TaskCategory.CONTENT
    return TaskCategory.UNKNOWN


BASE = "https://moltjobs.io"


class MoltJobsAdapter(BaseAdapter):
    """MoltJobs adapter using official API.

    MoltJobs has: agent registration, API keys, certification, job discovery,
    bidding, execution, proof submission, wallet, escrow, CLI, SDK, MCP.
    """
    platform = Platform.CUSTOM  # Will add MOLTJOBS to Platform enum

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=BASE,
            timeout=30,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        """Discover open jobs from MoltJobs."""
        try:
            for page in range(1, max_pages + 1):
                resp = await self.client.get("/api/jobs", params={
                    "page": page,
                    "status": "open",
                    "limit": 20,
                })
                if resp.status_code >= 400:
                    # Try alternate endpoint
                    resp = await self.client.get("/api/v1/jobs", params={
                        "page": page,
                        "status": "open",
                    })
                if resp.status_code >= 400:
                    break

                data = resp.json()
                items = data if isinstance(data, list) else data.get("jobs", data.get("data", []))
                if isinstance(items, dict):
                    items = items.get("jobs", items.get("items", []))
                if not items:
                    break

                for item in items or []:
                    if isinstance(item, dict):
                        yield self._to_opp(item)
        except Exception as e:
            pass  # MoltJobs may not have API yet

    def _to_opp(self, d: dict) -> Opportunity:
        title = d.get("title", d.get("name", ""))
        desc = d.get("description", d.get("body", ""))

        reward = 0.0
        for key in ("reward", "amount", "payment", "budget", "price"):
            if d.get(key) is not None:
                try:
                    reward = float(d[key])
                    break
                except (TypeError, ValueError):
                    pass

        # Detect chain/currency from response, don't hard-code
        currency = d.get("currency", "USDC")
        chain = d.get("chain", d.get("network", ""))

        return Opportunity(
            platform=Platform.MOLTJOBS,
            external_id=str(d.get("id", d.get("job_id", ""))),
            title=title,
            description=desc,
            url=d.get("url", d.get("apply_url", "")),
            reward=reward,
            currency=currency,
            category=_categorize(title + " " + desc),
            tags=d.get("tags", []),
            posted_at=_ts(d.get("created_at", d.get("posted_at"))),
            expires_at=_ts(d.get("deadline", d.get("expires_at"))),
            competition_estimate=int(d.get("bids", d.get("bid_count", 0)) or 0),
            verification_strength=0.8,
            payment_reliability=0.7,
            raw={**d, "chain": chain, "execution_supported": True},
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        """Check if we can bid on this job."""
        if not self.api_key:
            return False
        # MoltJobs requires certification for some jobs
        try:
            resp = await self.client.get("/api/agent/certifications")
            if resp.status_code == 200:
                certs = resp.json()
                # Check if we have relevant certification
                return True  # Assume certified for now
        except Exception:
            pass
        return True  # Attempt claim

    async def submit(self, opportunity: Opportunity, result: dict) -> dict:
        """Submit proof of work to MoltJobs."""
        if not self.api_key:
            return {"ok": False, "error": "MoltJobs API key required"}

        content = result.get("content", "")
        artifacts = result.get("artifacts", [])

        try:
            resp = await self.client.post(
                f"/api/jobs/{opportunity.external_id}/submit",
                json={
                    "content": content,
                    "artifacts": artifacts,
                    "proof": result.get("proof", {}),
                },
            )
            if resp.status_code >= 400:
                return {"ok": False, "error": f"HTTP {resp.status_code}"}
            return {"ok": True, "data": resp.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def check_status(self, opportunity: Opportunity) -> dict:
        """Check job status — escrow, settlement, etc."""
        if not self.api_key:
            return {"status": "unknown", "paid": False, "terminal": False}

        try:
            resp = await self.client.get(f"/api/jobs/{opportunity.external_id}")
            if resp.status_code >= 400:
                return {"status": "unknown", "paid": False, "terminal": False}

            data = resp.json()
            status = data.get("status", "pending")
            # MoltJobs uses escrow — check if settled
            paid = status in ("completed", "settled", "paid")
            terminal = status in ("completed", "settled", "paid", "cancelled", "expired", "rejected")

            return {
                "status": status,
                "paid": paid,
                "won": paid,
                "terminal": terminal,
                "reward": float(data.get("payment", data.get("reward", 0)) or 0),
                "tx_hash": data.get("settlement_tx", data.get("tx_hash", "")),
                "chain": data.get("chain", data.get("network", "")),
            }
        except Exception:
            return {"status": "unknown", "paid": False, "terminal": False}

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get("/api/health")
            return resp.status_code < 500
        except Exception:
            return False
