"""Oracle — discovers and scores jobs for the builder.

Separate process: scans marketplaces, normalizes opportunities,
scores them on internal metrics, feeds ranked list to builder.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from get_me_money.config import Config
from get_me_money.evaluator import Evaluator
from get_me_money.ledger import load_opportunities, save_opportunity
from get_me_money.main import get_adapters
from get_me_money.models import Opportunity, Platform

log = logging.getLogger(__name__)


async def discover_and_score(config: Config) -> list[dict]:
    """Discover opportunities, score them, return ranked list."""
    adapters = get_adapters(config)
    evaluator = Evaluator(config)

    # 1. Scan all platforms
    all_opps: list[Opportunity] = []
    for platform, adapter in adapters.items():
        try:
            async for opp in adapter.discover(max_pages=3):
                all_opps.append(opp)
                save_opportunity(opp)
        except Exception as e:
            log.warning("Oracle scan error %s: %s", platform.value, e)

    # 2. Filter already attempted
    from get_me_money.ledger import load_attempts
    attempts = load_attempts()
    attempted_ids = {a.opportunity_id for a in attempts}
    fresh = [o for o in all_opps if o.id not in attempted_ids]

    # 3. Score each
    scored = []
    for opp in fresh:
        ev = evaluator.evaluate(opp)
        scored.append({
            "id": opp.id,
            "platform": opp.platform.value,
            "title": opp.title,
            "description": opp.description[:200],
            "reward": opp.reward,
            "currency": opp.currency,
            "category": opp.category.value,
            "competition": opp.competition_estimate,
            "ev_cash": round(ev.ev_cash, 4),
            "ev_total": round(ev.ev_total, 4),
            "p_success": round(ev.probability_of_success, 3),
            "estimated_cost": round(ev.estimated_cost, 4),
            "should_attempt": ev.should_attempt,
            "reasoning": ev.reasoning,
        })

    # 4. Rank by EV
    scored.sort(key=lambda x: x["ev_total"], reverse=True)
    return scored


async def oracle_loop(config: Config) -> None:
    """Run oracle continuously, updating job queue."""
    log.info("Oracle starting...")
    while True:
        try:
            ranked = await discover_and_score(config)
            # Save to queue file for builder to consume
            queue_path = config.data_dir / "oracle-queue.json"
            queue_path.write_text(json.dumps({
                "updated_at": time.time(),
                "count": len(ranked),
                "jobs": ranked,
            }, indent=2))
            log.info("Oracle: %d jobs scored, %d viable",
                     len(ranked), sum(1 for j in ranked if j["should_attempt"]))
        except Exception as e:
            log.error("Oracle error: %s", e)
        await asyncio.sleep(config.scan_interval_seconds)


def get_queue(config: Config) -> list[dict]:
    """Read current oracle queue."""
    queue_path = config.data_dir / "oracle-queue.json"
    if not queue_path.exists():
        return []
    try:
        data = json.loads(queue_path.read_text())
        return data.get("jobs", [])
    except Exception:
        return []
