"""Earn cycle — the ONE path that performs paid work.

All execution goes through run_submission_loop().
scan_all and reconcile_pending are the two external-facing operations.
"""
from __future__ import annotations

import logging
from typing import Any

from get_me_money.config import Config
from get_me_money.evaluator import Evaluator
from get_me_money.ledger import (
    get_daily_spend, get_lifetime_spend,
    load_attempts, load_opportunities,
    save_attempt, save_opportunity,
)
from get_me_money.loop import run_submission_loop
from get_me_money.models import Attempt, Evaluation, Opportunity, Outcome, Platform
from get_me_money.platforms import BaseAdapter
from get_me_money.platforms.taskmarket import TaskmarketAdapter
from get_me_money.platforms.superteam import SuperteamAdapter
from get_me_money.platforms.moltjobs import MoltJobsAdapter

log = logging.getLogger(__name__)


def get_adapters(config: Config) -> dict[Platform, BaseAdapter]:
    """Get all enabled adapters."""
    out: dict[Platform, BaseAdapter] = {}
    if config.platforms.taskmarket_enabled:
        out[Platform.TASKMARKET] = TaskmarketAdapter()
    if config.platforms.superteam_enabled and config.platforms.superteam_key:
        out[Platform.SUPERTEAM] = SuperteamAdapter(
            config.platforms.superteam_key, config.platforms.superteam_telegram)
    if config.platforms.moltjobs_enabled and config.platforms.moltjobs_api_key:
        out[Platform.MOLTJOBS] = MoltJobsAdapter(config.platforms.moltjobs_api_key)
    return out


def get_adapter(config: Config, platform: Platform) -> BaseAdapter | None:
    """Get adapter for a specific platform."""
    adapters = get_adapters(config)
    return adapters.get(platform)


async def scan_all(config: Config) -> dict[str, Any]:
    """Scan all enabled platforms for opportunities."""
    adapters = get_adapters(config)
    existing = load_opportunities()
    known = {o.fingerprint(): o for o in existing}
    summary: dict[str, Any] = {"platforms": {}, "total_new": 0, "total_seen": 0}

    for p, adapter in adapters.items():
        new = 0
        try:
            async for opp in adapter.discover(max_pages=3):
                summary["total_seen"] += 1
                fp = opp.fingerprint()
                if fp not in known:
                    new += 1
                    known[fp] = opp
                else:
                    opp.id = known[fp].id
                    known[fp] = opp
                save_opportunity(opp)
            summary["platforms"][p.value] = {"status": "ok", "new": new}
            summary["total_new"] += new
        except Exception as e:
            summary["platforms"][p.value] = {"status": "error", "error": str(e), "new": 0}
    return summary


async def reconcile_pending(config: Config) -> list[dict]:
    """Check status of all pending attempts."""
    adapters = get_adapters(config)
    opp_by_id = {o.id: o for o in load_opportunities()}
    changes = []

    for a in load_attempts():
        if a.outcome != Outcome.PENDING:
            continue
        opp = opp_by_id.get(a.opportunity_id)
        adapter = adapters.get(a.platform)
        if not opp or not adapter:
            continue

        old = a.outcome
        try:
            status = await adapter.check_status(opp)
        except Exception:
            continue

        # Apply terminal status
        if status.get("paid"):
            reward = float(status.get("worker_payment", status.get("reward", 0)) or 0)
            fees = float(status.get("fee", 0) or 0)
            a.finalize(Outcome.SUCCEEDED, reward=reward, fees=fees)
            if status.get("tx_hash"):
                a.metadata["settlement_tx_hash"] = status["tx_hash"]
        elif status.get("terminal") and status.get("won") is False:
            a.finalize(Outcome.REJECTED)

        if a.outcome != old:
            save_attempt(a)
            changes.append({
                "attempt_id": a.id,
                "outcome": a.outcome.value,
                "reward": a.reward,
                "net": a.net,
            })
    return changes


async def earn_cycle(config: Config, execute: bool = False) -> dict[str, Any]:
    """The ONE earn cycle. scan → evaluate → loop → record."""
    daily = get_daily_spend()
    lifetime = get_lifetime_spend()
    if daily >= config.budget.daily_cap:
        return {"status": "daily_budget_exhausted", "daily_spend": daily}
    if lifetime >= config.budget.lifetime_cap:
        return {"status": "lifetime_budget_exhausted", "lifetime_spend": lifetime}

    scan = await scan_all(config)

    opps = load_opportunities()
    attempts = load_attempts()
    attempted_ids = {a.opportunity_id for a in attempts if a.outcome != Outcome.BLOCKED or a.cost > 0}
    candidates = [o for o in opps if o.id not in attempted_ids]

    evaluator = Evaluator(config)
    ranked = evaluator.rank([(o, evaluator.evaluate(o)) for o in candidates])
    viable = [(o, e) for o, e in ranked if e.should_attempt]
    preview = [{"id": o.id, "platform": o.platform.value, "title": o.title,
                "reward": o.reward, "p": round(e.probability_of_success, 3),
                "cash_ev": round(e.ev_cash, 4)} for o, e in ranked[:20]]

    if not execute or not viable:
        return {"status": "dry_run" if not execute else "no_viable_opportunities",
                "scan": scan, "viable": len(viable), "ranked": preview}

    from pathlib import Path
    import time
    results = []

    for opp, ev in viable[:config.max_attempts_per_cycle]:
        adapter = get_adapter(config, opp.platform)
        work_dir = config.work_dir / f"run-{opp.id[:20]}-{int(time.time())}"
        work_dir.mkdir(parents=True, exist_ok=True)

        log.info(f"Running loop on: {opp.title[:60]} (${opp.reward:.2f})")
        loop_result = await run_submission_loop(
            config, opp, ev, adapter, work_dir,
            skip_submit=False,
        )

        if loop_result.attempt:
            save_attempt(loop_result.attempt)

        results.append({
            "attempt_id": loop_result.attempt.id if loop_result.attempt else "?",
            "submitted": loop_result.submitted,
            "candidates": len(loop_result.run.candidates) if loop_result.run else 0,
            "selected": loop_result.run.selected_candidate_version if loop_result.run else 0,
        })

    return {"status": "ok", "scan": scan, "viable": len(viable), "results": results}
