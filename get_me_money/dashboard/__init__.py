"""P&L computed only from the latest state of each real attempt."""
from __future__ import annotations
import json
import time
from get_me_money.config import DASHBOARD_DB
from get_me_money.ledger import load_attempts, load_opportunities
from get_me_money.models import Outcome, PnLSnapshot


def compute_pnl() -> PnLSnapshot:
    attempts = load_attempts()
    snap = PnLSnapshot(timestamp=time.time(), opportunities_seen=len(load_opportunities()))
    snap.opportunities_attempted = len(attempts)
    snap.pending = sum(a.outcome == Outcome.PENDING for a in attempts)
    snap.successes = sum(a.outcome == Outcome.SUCCEEDED for a in attempts)
    snap.failures = sum(a.outcome in {Outcome.FAILED, Outcome.TIMEOUT} for a in attempts)
    snap.skips = sum(a.outcome in {Outcome.SKIPPED, Outcome.BLOCKED, Outcome.REJECTED} for a in attempts)
    snap.gross_earned = sum(a.reward for a in attempts if a.outcome == Outcome.SUCCEEDED)
    snap.total_cost = sum(a.cost for a in attempts)
    snap.total_fees = sum(a.fees for a in attempts)
    snap.net_earned = snap.gross_earned - snap.total_cost - snap.total_fees
    if snap.total_cost + snap.total_fees > 0:
        snap.roi_pct = 100 * snap.net_earned / (snap.total_cost + snap.total_fees)

    by_platform: dict[str, float] = {}
    by_cat: dict[str, dict] = {}
    for a in attempts:
        by_platform[a.platform.value] = by_platform.get(a.platform.value, 0) + a.net
        cat = str(a.metadata.get("category", "unknown"))
        row = by_cat.setdefault(cat, {"attempts": 0, "successes": 0, "total_net": 0.0})
        row["attempts"] += 1
        row["successes"] += int(a.outcome == Outcome.SUCCEEDED)
        row["total_net"] += a.net
    if by_platform:
        snap.best_platform = max(by_platform, key=by_platform.get)
    if by_cat:
        snap.best_category = max(by_cat, key=lambda k: by_cat[k]["total_net"])
    snap.strategies = {
        cat: {"attempts": r["attempts"], "win_rate": r["successes"] / max(1, r["attempts"]), "avg_net": r["total_net"] / max(1, r["attempts"])}
        for cat, r in by_cat.items()
    }
    return snap


def snapshot_dict(s: PnLSnapshot | None = None) -> dict:
    s = s or compute_pnl()
    return {
        "timestamp": s.timestamp, "opportunities_seen": s.opportunities_seen,
        "opportunities_attempted": s.opportunities_attempted, "pending": s.pending,
        "successes": s.successes, "failures": s.failures, "skips": s.skips,
        "gross_earned": round(s.gross_earned, 6), "total_cost": round(s.total_cost, 6),
        "total_fees": round(s.total_fees, 6), "net_earned": round(s.net_earned, 6),
        "roi_pct": round(s.roi_pct, 2), "best_platform": s.best_platform,
        "best_category": s.best_category, "strategies": s.strategies,
    }


def save_pnl(s: PnLSnapshot | None = None) -> dict:
    d = snapshot_dict(s)
    DASHBOARD_DB.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DB.write_text(json.dumps(d, indent=2))
    return d


def get_dashboard_data() -> dict:
    return save_pnl()
