"""Deterministic economic controller. Hermes does work; controller owns money/marketplace decisions."""
from __future__ import annotations

import logging
from typing import Any

from get_me_money.config import Config
from get_me_money.dashboard import save_pnl
from get_me_money.evaluator import Evaluator
from get_me_money.executor import Executor
from get_me_money.ledger import get_daily_spend, get_lifetime_spend, load_attempts, load_opportunities, save_attempt, save_opportunity
from get_me_money.models import Opportunity, Outcome, Platform
from get_me_money.notifier import notify
from get_me_money.platforms import BaseAdapter
from get_me_money.platforms.bounty import BountyAdapter
from get_me_money.platforms.moltjobs import MoltJobsAdapter
from get_me_money.platforms.taskmarket import TaskmarketAdapter
from get_me_money.platforms.superteam import SuperteamAdapter

log = logging.getLogger(__name__)


def get_adapters(config: Config) -> dict[Platform, BaseAdapter]:
    out: dict[Platform, BaseAdapter] = {}
    if config.platforms.bounty_enabled:
        out[Platform.BOUNTY] = BountyAdapter(api_key=config.platforms.bounty_api_key)
    if config.platforms.taskmarket_enabled:
        out[Platform.TASKMARKET] = TaskmarketAdapter()
    if config.platforms.superteam_enabled and config.platforms.superteam_key:
        out[Platform.SUPERTEAM] = SuperteamAdapter(config.platforms.superteam_key, config.platforms.superteam_telegram)
    if config.platforms.moltjobs_enabled:
        out[Platform.MOLTJOBS] = MoltJobsAdapter(api_key=config.platforms.moltjobs_api_key)
    return out


async def scan_all(config: Config) -> dict[str, Any]:
    adapters = get_adapters(config)
    existing = load_opportunities()
    known = {o.fingerprint(): o for o in existing}
    summary = {"platforms": {}, "total_new": 0, "total_seen": 0}
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
                    # Preserve the controller ID so attempts reconcile across repeated scans.
                    opp.id = known[fp].id
                    known[fp] = opp
                # Always append the current snapshot; loader keeps latest fingerprint.
                save_opportunity(opp)
            summary["platforms"][p.value] = {"status": "ok", "new": new}
            summary["total_new"] += new
        except Exception as e:
            summary["platforms"][p.value] = {"status": "error", "error": str(e), "new": 0}
    return summary


async def reconcile_pending(config: Config) -> list[dict]:
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
        status = await adapter.check_status(opp)
        Executor.apply_status(a, status)
        if a.outcome != old:
            save_attempt(a)
            changes.append({"attempt_id": a.id, "outcome": a.outcome.value, "reward": a.reward, "net": a.net})
            if a.outcome == Outcome.SUCCEEDED:
                await notify(config, f"get-me-money earned ${a.reward:.4f} on {a.platform.value}: {a.title}\nNet after recorded costs/fees: ${a.net:.4f}")
    save_pnl()
    return changes


async def earn_cycle(config: Config, execute: bool = False) -> dict[str, Any]:
    await reconcile_pending(config)
    daily = get_daily_spend(); lifetime = get_lifetime_spend()
    if daily >= config.budget.daily_cap:
        return {"status": "daily_budget_exhausted", "daily_spend": daily}
    if lifetime >= config.budget.lifetime_cap:
        return {"status": "lifetime_budget_exhausted", "lifetime_spend": lifetime}

    scan = await scan_all(config)
    attempts = load_attempts()
    attempted_ids = {a.opportunity_id for a in attempts if a.outcome != Outcome.BLOCKED or a.cost > 0}
    candidates = [o for o in load_opportunities() if o.id not in attempted_ids]
    evaluator = Evaluator(config)
    ranked = evaluator.rank([(o, evaluator.evaluate(o)) for o in candidates])
    viable = [(o, e) for o, e in ranked if e.should_attempt]
    preview = [{"id":o.id,"platform":o.platform.value,"title":o.title,"reward":o.reward,"p":round(e.probability_of_success,3),"cash_ev":round(e.ev_cash,4),"est_cost":round(e.estimated_cost,4),"reason":e.reasoning} for o,e in ranked[:20]]

    if not execute or not viable:
        return {"status": "dry_run" if not execute else "no_viable_opportunities", "scan": scan, "viable": len(viable), "ranked": preview}

    adapters = get_adapters(config)
    executor = Executor(config, adapters)
    results = []
    remaining_daily = config.budget.daily_cap - daily
    remaining_lifetime = config.budget.lifetime_cap - lifetime

    for opp, ev in viable[:config.max_attempts_per_cycle]:
        if ev.estimated_cost > min(remaining_daily, remaining_lifetime, config.budget.per_attempt_cap):
            continue
        a = await executor.execute(opp, ev)
        save_attempt(a)
        results.append({"attempt_id":a.id,"platform":a.platform.value,"title":a.title,"outcome":a.outcome.value,"cost":a.cost,"reward":a.reward,"net":a.net,"error":a.error})
        remaining_daily -= a.cost + a.fees; remaining_lifetime -= a.cost + a.fees
        await notify(config, f"get-me-money submitted/attempted: {a.title}\nplatform={a.platform.value} outcome={a.outcome.value} cost=${a.cost:.4f}")
    # WorkRun → Moltwork integration happens inside executor._create_workrun()
    pnl = save_pnl()
    return {"status": "ok", "scan": scan, "viable": len(viable), "results": results, "pnl": pnl}
