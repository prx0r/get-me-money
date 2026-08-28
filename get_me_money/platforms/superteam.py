"""Official Superteam Earn agent API adapter.

Discovery is live when SUPERTEAM_KEY is configured. Auto-submit stays disabled unless
SUPERTEAM_AUTOSUBMIT=1 because many listings need a public deployment/link or human Telegram.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import AsyncIterator, Any
import httpx

from get_me_money.models import Opportunity, Platform, TaskCategory
from get_me_money.platforms import BaseAdapter

BASE = "https://superteam.fun"


def _ts(v: Any) -> float:
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str) and v:
        try: return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError: return 0.0
    return 0.0


def _reward(d: dict) -> float:
    for k in ("reward", "amount", "prize", "prizeAmount", "totalReward", "compensationMax", "maxReward"):
        try:
            if d.get(k) is not None: return float(d[k])
        except (TypeError, ValueError): pass
    return 0.0


def _cat(text: str) -> TaskCategory:
    t = text.lower()
    if any(x in t for x in ("code", "build", "developer", "github", "api")): return TaskCategory.CODE_FEATURE
    if any(x in t for x in ("research", "analysis", "data")): return TaskCategory.RESEARCH
    if any(x in t for x in ("write", "content", "article")): return TaskCategory.CONTENT
    if any(x in t for x in ("design", "figma", "ui", "ux")): return TaskCategory.DESIGN
    return TaskCategory.UNKNOWN


class SuperteamAdapter(BaseAdapter):
    platform = Platform.SUPERTEAM

    def __init__(self, api_key: str, telegram: str = ""):
        self.api_key = api_key
        self.telegram = telegram
        self.autosubmit = os.getenv("SUPERTEAM_AUTOSUBMIT", "0") == "1"
        self.client = httpx.AsyncClient(base_url=BASE, timeout=30, headers={"Authorization": f"Bearer {api_key}"})

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        take = min(100, max_pages * 20)
        r = await self.client.get("/api/agents/listings/live", params={"take": take})
        if r.status_code >= 400: return
        data = r.json()
        items = data if isinstance(data, list) else data.get("listings", data.get("data", []))
        if isinstance(items, dict): items = items.get("listings", items.get("items", []))
        for d in items or []:
            if not isinstance(d, dict): continue
            access = str(d.get("agentAccess", d.get("agent_access", "AGENT_ALLOWED")))
            if access not in {"AGENT_ALLOWED", "AGENT_ONLY"}: continue
            yield self._to_opp(d)

    def _to_opp(self, d: dict) -> Opportunity:
        title = str(d.get("title", d.get("name", "")))
        desc = str(d.get("description", d.get("body", d.get("shortDescription", ""))))
        kind = str(d.get("type", d.get("listingType", ""))).lower()
        supported = self.autosubmit and kind == "bounty"
        block = "Superteam is discovery-only until SUPERTEAM_AUTOSUBMIT=1; projects/hackathons often need public deployment or human fields"
        return Opportunity(
            platform=Platform.SUPERTEAM, external_id=str(d.get("id", d.get("listingId", ""))),
            title=title, description=desc, url=str(d.get("url", d.get("slug", ""))),
            reward=_reward(d), currency=str(d.get("currency", "USDC")), category=_cat(title + " " + desc),
            tags=list(d.get("skills", d.get("tags", [])) or []), posted_at=_ts(d.get("createdAt")),
            expires_at=_ts(d.get("deadline")), competition_estimate=int(d.get("submissionCount", d.get("submissions", 0)) or 0),
            verification_strength=.8, payment_reliability=.85,
            raw={**d, "execution_supported": supported, "execution_block_reason": block},
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        return bool(opportunity.raw.get("execution_supported"))

    async def submit(self, opportunity: Opportunity, result: dict) -> dict:
        sub = result.get("submission", {}) if isinstance(result.get("submission"), dict) else {}
        kind = str(opportunity.raw.get("type", opportunity.raw.get("listingType", ""))).lower()
        telegram = self.telegram if kind == "project" else (self.telegram or "")
        if kind == "project" and not telegram:
            return {"ok": False, "error": "project requires human Telegram URL; set SUPERTEAM_TELEGRAM"}
        payload = {
            "listingId": opportunity.external_id,
            "link": str(sub.get("link", result.get("url", ""))),
            "tweet": str(sub.get("tweet", "")),
            "otherInfo": str(sub.get("otherInfo", result.get("content", "")))[:20000],
            "eligibilityAnswers": sub.get("eligibilityAnswers", []),
            "ask": sub.get("ask"),
            "telegram": telegram,
        }
        r = await self.client.post("/api/agents/submissions/create", json=payload)
        if r.status_code >= 400:
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:1000]}"}
        return {"ok": True, "raw": r.json()}

    async def check_status(self, opportunity: Opportunity) -> dict:
        # Official agent docs currently expose create/update/comment/claim flows but no
        # canonical per-agent result endpoint. Keep as pending; human claim/result can
        # be reconciled manually until an official read path is documented.
        return {"status": "pending", "paid": False, "terminal": False}

    async def health_check(self) -> bool:
        try:
            r = await self.client.get("/api/agents/listings/live", params={"take": 1})
            return r.status_code < 500
        except Exception:
            return False

    @staticmethod
    async def register(name: str) -> dict:
        async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
            r = await client.post("/api/agents", json={"name": name})
            if r.status_code >= 400:
                raise RuntimeError(f"Superteam registration HTTP {r.status_code}: {r.text[:1000]}")
            return r.json()
