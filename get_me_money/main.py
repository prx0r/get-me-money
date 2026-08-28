"""Earn cycle — the ONE path that performs paid work.

All execution goes through run_submission_loop().
No legacy Executor. No parallel architectures.
"""
from __future__ import annotations

import logging
from typing import Any

from get_me_money.config import Config
from get_me_money.evaluator import Evaluator
from get_me_money.ledger import get_daily_spend, get_lifetime_spend, load_attempts, load_opportunities, save_attempt
from get_me_money.loop import run_submission_loop
from get_me_money.models import Attempt, Evaluation, Opportunity, Outcome, Platform
from get_me_money.platforms import BaseAdapter
from get_me_money.platforms.taskmarket import TaskmarketAdapter
from get_me_money.platforms.superteam import SuperteamAdapter
from get_me_money.platforms.moltjobs import MoltJobsAdapter

log = logging.getLogger(__name__)


def get_adapter(config: Config, platform: Platform) -> BaseAdapter | None:
    """Get the adapter for a platform."""
    adapters = {
        Platform.TASKMARKET: TaskmarketAdapter,
        Platform.SUPERTEAM: lambda: SuperteamAdapter(config.platforms.superteam_key, config.platforms.superteam_telegram) if config.platforms.superteam_key else None,
        Platform.MOLTJOBS: lambda: MoltJobsAdapter(config.platforms.moltjobs_api_key) if config.platforms.moltjobs_api_key else None,
    }
    factory = adapters.get(platform)
    if factory:
        result = factory()
        return result if result else None
    return None


async def earn_cycle(config: Config, execute: bool = False) -> dict[str, Any]:
    """The ONE earn cycle. scan → evaluate → loop → record."""
    # Check budget
    daily = get_daily_spend()
    lifetime = get_lifetime_spend()
    if daily >= config.budget.daily_cap:
        return {"status": "daily_budget_exhausted", "daily_spend": daily}
    if lifetime >= config.budget.lifetime_cap:
        return {"status": "lifetime_budget_exhausted", "lifetime_spend": lifetime}

    # Scan for opportunities
    from get_me_money.main import scan_all
    scan = await scan_all(config)

    # Load and rank candidates
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

    # Execute the loop on the best candidate
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

        # Save attempt
        if loop_result.attempt:
            save_attempt(loop_result.attempt)

        results.append({
            "attempt_id": loop_result.attempt.id if loop_result.attempt else "?",
            "submitted": loop_result.submitted,
            "candidates": len(loop_result.run.candidates) if loop_result.run else 0,
            "selected": loop_result.run.selected_candidate_version if loop_result.run else 0,
        })

    return {"status": "ok", "scan": scan, "viable": len(viable), "results": results}
