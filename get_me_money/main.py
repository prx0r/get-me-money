"""Main orchestrator — the brain that ties everything together."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from get_me_money.config import Config
from get_me_money.dashboard import compute_pnl, save_pnl
from get_me_money.evaluator import Evaluator
from get_me_money.executor import Executor
from get_me_money.ledger import (
    get_daily_spend, load_opportunities, save_opportunity, save_attempt,
)
from get_me_money.memory import Memory
from get_me_money.models import Opportunity, Platform, Outcome
from get_me_money.platforms import BaseAdapter
from get_me_money.platforms.algora import AlgoraAdapter
from get_me_money.platforms.bounty import BountyAdapter
from get_me_money.platforms.clustly import ClustlyAdapter
from get_me_money.platforms.gigs import GigsAdapter
from get_me_money.platforms.opire import OpireAdapter
from get_me_money.platforms.superteam import SuperteamAdapter
from get_me_money.platforms.taskmarket import TaskmarketAdapter

log = logging.getLogger(__name__)


def get_adapters(config: Config) -> dict[Platform, BaseAdapter]:
    """Initialize enabled platform adapters."""
    pc = config.platforms
    adapters: dict[Platform, BaseAdapter] = {}

    if pc.taskmarket_enabled:
        adapters[Platform.TASKMARKET] = TaskmarketAdapter(api_key=pc.taskmarket_api_key)
    if pc.bounty_enabled:
        adapters[Platform.BOUNTY] = BountyAdapter(api_key=pc.bounty_api_key)
    if pc.algora_enabled:
        adapters[Platform.ALGORA] = AlgoraAdapter(token=pc.algora_token)
    if pc.opire_enabled:
        adapters[Platform.OPIRE] = OpireAdapter(token=pc.opire_token)
    if pc.clustly_enabled:
        adapters[Platform.CLUSTLY] = ClustlyAdapter(token=pc.clustly_token)
    if pc.superteam_enabled:
        adapters[Platform.SUPERTEAM] = SuperteamAdapter(api_key=pc.superteam_key)

    # Always include gigs.sh for discovery
    adapters[Platform.GIGS] = GigsAdapter()

    return adapters


async def scan_all(config: Config) -> dict[str, Any]:
    """Scan all platforms, save new opportunities, return summary."""
    adapters = get_adapters(config)
    summary: dict[str, Any] = {"platforms": {}, "total_new": 0, "total_seen": 0}

    existing = load_opportunities()
    existing_fps = {o.fingerprint() for o in existing}

    for platform, adapter in adapters.items():
        if platform == Platform.GIGS:
            continue  # Directory, not jobs
        try:
            count = 0
            async for opp in adapter.discover(max_pages=3):
                fp = opp.fingerprint()
                if fp not in existing_fps:
                    save_opportunity(opp)
                    existing_fps.add(fp)
                    count += 1
                summary["total_seen"] += 1
            summary["platforms"][platform.value] = {"new": count, "status": "ok"}
            summary["total_new"] += count
        except Exception as e:
            summary["platforms"][platform.value] = {"new": 0, "status": f"error: {e}"}

    return summary


async def earn_cycle(config: Config, dry_run: bool = False) -> dict[str, Any]:
    """Full earn cycle: scan → evaluate → attempt → record → learn."""
    budget = config.budget
    daily_spend = get_daily_spend()

    if daily_spend >= budget.daily_cap:
        return {"status": "budget_exhausted", "daily_spend": daily_spend}

    # 1. Scan
    log.info("Scanning platforms...")
    scan_result = await scan_all(config)

    # 2. Load all opportunities
    all_opps = load_opportunities()
    log.info("Loaded %d opportunities", len(all_opps))

    # 3. Filter: already attempted?
    from get_me_money.ledger import load_attempts
    attempts = load_attempts()
    attempted_ids = {a.opportunity_id for a in attempts}

    fresh_opps = [o for o in all_opps if o.id not in attempted_ids]
    log.info("%d fresh opportunities (not yet attempted)", len(fresh_opps))

    # 4. Evaluate
    evaluator = Evaluator(config)
    evaluated: list[tuple[Opportunity, Any]] = []
    for opp in fresh_opps:
        ev = evaluator.evaluate(opp)
        evaluated.append((opp, ev))

    ranked = evaluator.rank(evaluated)
    to_attempt = [(o, e) for o, e in ranked if e.should_attempt]
    log.info("%d opportunities pass EV gate", len(to_attempt))

    if not to_attempt:
        return {
            "status": "no_viable_opportunities",
            "scan": scan_result,
            "evaluated": len(evaluated),
            "viable": 0,
        }

    # 5. Execute (within budget)
    adapters = get_adapters(config)
    executor = Executor(config, adapters)
    memory = Memory()
    memory.load()

    results: list[dict] = []
    remaining_budget = budget.daily_cap - daily_spend

    for opp, ev in to_attempt[:config.max_concurrent_attempts]:
        if ev.estimated_cost > min(remaining_budget, budget.per_attempt_cap):
            log.info("Skipping %s — cost $%.2f exceeds remaining budget $%.2f",
                     opp.title, ev.estimated_cost, remaining_budget)
            continue

        if dry_run:
            results.append({
                "opportunity": opp.title,
                "platform": opp.platform.value,
                "reward": opp.reward,
                "ev_total": round(ev.ev_total, 2),
                "p_success": round(ev.probability_of_success, 2),
                "estimated_cost": round(ev.estimated_cost, 2),
                "action": "dry_run",
            })
            continue

        log.info("Attempting: %s (EV=$%.2f, P=%.0f%%)",
                 opp.title, ev.ev_total, ev.probability_of_success * 100)

        attempt = await executor.execute(opp, ev)
        attempt.metadata = {"category": opp.category.value}
        save_attempt(attempt)
        memory.record(attempt)
        remaining_budget -= attempt.cost + attempt.fees

        results.append({
            "opportunity": opp.title,
            "platform": opp.platform.value,
            "outcome": attempt.outcome.value,
            "reward": attempt.reward,
            "cost": round(attempt.cost, 4),
            "net": round(attempt.net, 4),
            "duration_s": round(attempt.duration_seconds, 1),
        })

    # 6. Update P&L
    snap = compute_pnl()
    save_pnl(snap)

    return {
        "status": "ok",
        "scan": scan_result,
        "evaluated": len(evaluated),
        "viable": len(to_attempt),
        "attempted": len([r for r in results if r.get("action") != "dry_run"]),
        "results": results,
        "pnl": {
            "net_earned": round(snap.net_earned, 2),
            "roi_pct": round(snap.roi_pct, 1),
        },
    }
