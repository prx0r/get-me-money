"""Taskmarket adapter using the first-party CLI for wallet/signature/legal handling."""
from __future__ import annotations

import asyncio
import json
import shutil
import time
from datetime import datetime
from typing import AsyncIterator, Any

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


def _usdc(data: dict, key: str = "reward") -> float:
    for k in (f"{key}Usdc", f"{key}_usdc", "rewardUsdc", "reward_usdc"):
        if data.get(k) is not None:
            try:
                return float(data[k])
            except (TypeError, ValueError):
                pass
    raw = data.get(key, data.get("reward", 0))
    try:
        # Taskmarket raw task values are USDC base units (6 decimals).
        return float(int(str(raw))) / 1_000_000.0
    except (TypeError, ValueError):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0


def _categorize(text: str) -> TaskCategory:
    t = text.lower()
    if any(x in t for x in ("bug", "code", "repo", "github", "implement", "fix")):
        return TaskCategory.CODE_FIX
    if any(x in t for x in ("extract", "dataset", "csv", "scrape")):
        return TaskCategory.DATA_EXTRACTION
    if any(x in t for x in ("api", "x402", "integration", "endpoint")):
        return TaskCategory.API_WORK
    if any(x in t for x in ("research", "analysis", "map", "compare", "ideas")):
        return TaskCategory.RESEARCH
    if any(x in t for x in ("write", "content", "article", "documentation")):
        return TaskCategory.CONTENT
    return TaskCategory.UNKNOWN


class TaskmarketAdapter(BaseAdapter):
    platform = Platform.TASKMARKET

    def __init__(self, binary: str = "taskmarket"):
        self.binary = binary

    async def _run(self, *args: str, timeout: int = 60) -> dict:
        binary = shutil.which(self.binary) or self.binary
        try:
            p = await asyncio.create_subprocess_exec(binary, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, err = await asyncio.wait_for(p.communicate(), timeout=timeout)
        except (FileNotFoundError, asyncio.TimeoutError) as e:
            return {"ok": False, "error": str(e)}
        text = out.decode(errors="replace").strip()
        if p.returncode != 0:
            return {"ok": False, "error": err.decode(errors="replace").strip() or text}
        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and "ok" in payload:
                return payload
            return {"ok": True, "data": payload}
        except json.JSONDecodeError:
            return {"ok": True, "data": text}

    async def discover(self, max_pages: int = 3) -> AsyncIterator[Opportunity]:
        cursor = ""
        for _ in range(max_pages):
            args = ["task", "list", "--status", "open", "--mode", "bounty", "--limit", "20"]
            if cursor:
                args += ["--cursor", cursor]
            res = await self._run(*args)
            if not res.get("ok"):
                return
            data = res.get("data", {})
            items = data if isinstance(data, list) else data.get("tasks", data.get("items", []))
            if not items:
                return
            for item in items:
                if isinstance(item, dict):
                    yield self._to_opp(item)
            cursor = data.get("nextCursor", "") if isinstance(data, dict) else ""
            if not cursor:
                return

    def _to_opp(self, d: dict) -> Opportunity:
        desc = str(d.get("description", d.get("title", "")))
        title = str(d.get("title") or desc.splitlines()[0][:100] or d.get("id", "Taskmarket task"))
        submission_count = d.get("submissionCount", d.get("submission_count", 0)) or 0
        return Opportunity(
            platform=Platform.TASKMARKET,
            external_id=str(d.get("id", d.get("taskId", ""))),
            title=title, description=desc,
            url=str(d.get("url", "")), reward=_usdc(d), currency="USDC",
            category=_categorize(title + " " + desc),
            tags=list(d.get("tags", []) or []), posted_at=_ts(d.get("createdAt", d.get("created_at"))),
            expires_at=_ts(d.get("deadline", d.get("expiresAt", d.get("submissionDeadline")))),
            competition_estimate=int(submission_count), verification_strength=.85,
            payment_reliability=.85,
            raw={**d, "execution_supported": True},
        )

    async def claim(self, opportunity: Opportunity) -> bool:
        legal = await self._run("legal", "status")
        legal_data = legal.get("data") or {}
        accepted = bool(legal_data.get("accepted"))
        enforcement = legal_data.get("enforcementEnabled", True)
        if not accepted and enforcement:
            return False  # human/operator must review + accept; controller never does it.
        # If enforcement is disabled, proceed even without acceptance
        detail = await self._run("task", "get", opportunity.external_id)
        if not detail.get("ok"):
            return False
        data = detail.get("data") or {}
        actions = data.get("pendingActions", []) if isinstance(data, dict) else []
        if actions:
            return any(a.get("role") == "worker" and a.get("action") == "submit" for a in actions if isinstance(a, dict))
        return str(data.get("mode", "bounty")) == "bounty" and str(data.get("status", "open")) == "open"

    async def submit(self, opportunity: Opportunity, result: dict) -> dict:
        # Re-fetch immediately before the external write; task state may have changed while Hermes worked.
        detail = await self._run("task", "get", opportunity.external_id)
        if not detail.get("ok"):
            return {"ok": False, "error": "could not re-fetch task before submit"}
        d = detail.get("data") or {}
        actions = d.get("pendingActions", []) if isinstance(d, dict) else []
        if actions and not any(a.get("role") == "worker" and a.get("action") == "submit" for a in actions if isinstance(a, dict)):
            return {"ok": False, "error": "submission is no longer an allowed pending action"}
        artifacts = [str(x) for x in result.get("artifacts", []) if x]
        if not artifacts:
            return {"ok": False, "error": "no artifacts"}
        args = ["task", "submit", opportunity.external_id]
        for f in artifacts:
            args += ["--file", f]
        res = await self._run(*args, timeout=180)
        if not res.get("ok"):
            return res
        data = res.get("data") or {}
        return {"ok": True, "submission_id": data.get("submissionId", ""), "raw": data}

    async def _address(self) -> str:
        res = await self._run("address")
        data = res.get("data")
        if isinstance(data, str):
            return data.strip()
        if isinstance(data, dict):
            return str(data.get("address", data.get("walletAddress", "")))
        return ""

    async def check_status(self, opportunity: Opportunity) -> dict:
        detail = await self._run("task", "get", opportunity.external_id)
        if not detail.get("ok"):
            return {"status": "unknown"}
        d = detail.get("data") or {}
        address = (await self._address()).lower()
        awards = d.get("awards", []) or []
        for aw in awards:
            if str(aw.get("workerAddress", "")).lower() == address and address:
                gross = _usdc(aw, "grossAmount")
                paid = _usdc(aw, "workerPayment")
                return {
                    "status": "paid", "paid": True, "won": True,
                    "worker_payment": paid, "reward": paid,
                    "fee": max(0.0, gross - paid), "tx_hash": aw.get("settlementTxHash", ""),
                }
        status = str(d.get("status", "")).lower()
        phase = str(d.get("phase", "")).lower()
        terminal = status in {"completed", "cancelled", "expired"} or phase in {"settled", "completed", "cancelled"}
        return {"status": status or phase or "pending", "paid": False, "won": False if terminal else None, "terminal": terminal}

    async def health_check(self) -> bool:
        return bool((await self._run("task", "list", "--status", "open", "--limit", "1")).get("ok"))
