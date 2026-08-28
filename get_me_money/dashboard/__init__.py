"""P&L tracker — compute and persist profit/loss snapshots."""

from __future__ import annotations

import json
import time
from pathlib import Path

from get_me_money.config import DASHBOARD_DB
from get_me_money.ledger import load_attempts
from get_me_money.models import Outcome, PnLSnapshot


def compute_pnl() -> PnLSnapshot:
    """Compute current P&L from all recorded attempts."""
    attempts = load_attempts()
    snap = PnLSnapshot(timestamp=time.time())

    snap.opportunities_attempted = len(attempts)
    snap.successes = sum(1 for a in attempts if a.outcome == Outcome.SUCCEEDED)
    snap.failures = sum(1 for a in attempts if a.outcome == Outcome.FAILED)
    snap.skips = sum(1 for a in attempts if a.outcome in (Outcome.SKIPPED, Outcome.REJECTED))
    snap.gross_earned = sum(a.reward for a in attempts)
    snap.total_cost = sum(a.cost for a in attempts)
    snap.total_fees = sum(a.fees for a in attempts)
    snap.net_earned = snap.gross_earned - snap.total_cost - snap.total_fees

    if snap.total_cost > 0:
        snap.roi_pct = (snap.net_earned / snap.total_cost) * 100

    # Platform breakdown
    platform_totals: dict[str, float] = {}
    for a in attempts:
        p = a.platform
        platform_totals[p] = platform_totals.get(p, 0) + a.net
    if platform_totals:
        best = max(platform_totals, key=platform_totals.get)
        snap.best_platform = best.value if hasattr(best, 'value') else str(best)

    # Category breakdown
    cat_totals: dict[str, float] = {}
    for a in attempts:
        cat = a.metadata.get("category", "unknown") if hasattr(a, 'metadata') else "unknown"
        cat_totals[cat] = cat_totals.get(cat, 0) + a.net
    if cat_totals:
        snap.best_category = max(cat_totals, key=cat_totals.get)

    # Strategy summary
    strategies: dict[str, dict] = {}
    for a in attempts:
        cat = a.metadata.get("category", "unknown") if hasattr(a, 'metadata') else "unknown"
        key = f"{cat}"
        if key not in strategies:
            strategies[key] = {"attempts": 0, "successes": 0, "total_net": 0, "total_reward": 0}
        strategies[key]["attempts"] += 1
        if a.outcome == Outcome.SUCCEEDED:
            strategies[key]["successes"] += 1
        strategies[key]["total_net"] += a.net
        strategies[key]["total_reward"] += a.reward

    snap.strategies = {}
    for cat, s in strategies.items():
        win_rate = s["successes"] / max(1, s["attempts"])
        avg_net = s["total_net"] / max(1, s["attempts"])
        snap.strategies[cat] = {
            "attempts": s["attempts"],
            "win_rate": round(win_rate, 3),
            "avg_net": round(avg_net, 2),
            "total_reward": round(s["total_reward"], 2),
        }

    return snap


def save_pnl(snap: PnLSnapshot) -> None:
    """Save P&L snapshot to dashboard JSON."""
    data = {
        "timestamp": snap.timestamp,
        "opportunities_seen": snap.opportunities_seen,
        "opportunities_attempted": snap.opportunities_attempted,
        "successes": snap.successes,
        "failures": snap.failures,
        "skips": snap.skips,
        "gross_earned": round(snap.gross_earned, 2),
        "total_cost": round(snap.total_cost, 2),
        "total_fees": round(snap.total_fees, 2),
        "net_earned": round(snap.net_earned, 2),
        "roi_pct": round(snap.roi_pct, 1),
        "best_platform": snap.best_platform,
        "best_category": snap.best_category,
        "strategies": snap.strategies,
    }
    DASHBOARD_DB.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DB.write_text(json.dumps(data, indent=2, default=str))


def get_dashboard_data() -> dict:
    """Read the latest dashboard JSON, or compute fresh."""
    if DASHBOARD_DB.exists():
        try:
            return json.loads(DASHBOARD_DB.read_text())
        except Exception:
            pass
    snap = compute_pnl()
    save_pnl(snap)
    return {
        "timestamp": snap.timestamp,
        "opportunities_attempted": snap.opportunities_attempted,
        "successes": snap.successes,
        "failures": snap.failures,
        "gross_earned": round(snap.gross_earned, 2),
        "total_cost": round(snap.total_cost, 2),
        "total_fees": round(snap.total_fees, 2),
        "net_earned": round(snap.net_earned, 2),
        "roi_pct": round(snap.roi_pct, 1),
        "best_platform": snap.best_platform,
        "best_category": snap.best_category,
        "strategies": snap.strategies,
    }
