"""Ledger — JSONL-based persistence for opportunities, attempts, strategies."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator

from get_me_money.config import (
    ATTEMPTS_DB, DATA_DIR, OPPORTUNITIES_DB, STRATEGIES_DB,
)
from get_me_money.models import Attempt, Opportunity, Outcome, Platform, Strategy, TaskCategory


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _read_all(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


# --- Opportunities ---

def save_opportunity(opp: Opportunity) -> None:
    _append(OPPORTUNITIES_DB, {
        "id": opp.id,
        "platform": opp.platform.value,
        "external_id": opp.external_id,
        "title": opp.title,
        "description": opp.description[:1000],
        "url": opp.url,
        "reward": opp.reward,
        "currency": opp.currency,
        "category": opp.category.value,
        "tags": opp.tags,
        "posted_at": opp.posted_at,
        "competition_estimate": opp.competition_estimate,
        "verification_strength": opp.verification_strength,
        "payment_reliability": opp.payment_reliability,
        "fetched_at": opp.fetched_at,
    })


def load_opportunities() -> list[Opportunity]:
    seen = set()
    opps = []
    for r in _read_all(OPPORTUNITIES_DB):
        fp = f"{r['platform']}:{r['external_id']}:{r['title']}"
        if fp in seen:
            continue
        seen.add(fp)
        opps.append(Opportunity(
            id=r["id"],
            platform=Platform(r["platform"]),
            external_id=r.get("external_id", ""),
            title=r.get("title", ""),
            description=r.get("description", ""),
            url=r.get("url", ""),
            reward=r.get("reward", 0),
            currency=r.get("currency", "USD"),
            category=TaskCategory(r.get("category", "unknown")),
            tags=r.get("tags", []),
            posted_at=r.get("posted_at", 0),
            competition_estimate=r.get("competition_estimate", 0),
            verification_strength=r.get("verification_strength", 0.5),
            payment_reliability=r.get("payment_reliability", 0.5),
            fetched_at=r.get("fetched_at", 0),
        ))
    return opps


# --- Attempts ---

def save_attempt(attempt: Attempt) -> None:
    _append(ATTEMPTS_DB, {
        "id": attempt.id,
        "opportunity_id": attempt.opportunity_id,
        "platform": attempt.platform.value,
        "external_id": attempt.external_id,
        "title": attempt.title,
        "outcome": attempt.outcome.value,
        "reward": attempt.reward,
        "cost": attempt.cost,
        "fees": attempt.fees,
        "net": attempt.net,
        "duration_seconds": attempt.duration_seconds,
        "error": attempt.error,
        "submission_url": attempt.submission_url,
        "notes": attempt.notes,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
    })


def load_attempts() -> list[Attempt]:
    return [
        Attempt(
            id=r["id"],
            opportunity_id=r.get("opportunity_id", ""),
            platform=Platform(r["platform"]) if isinstance(r["platform"], str) else r["platform"],
            external_id=r.get("external_id", ""),
            title=r.get("title", ""),
            outcome=Outcome(r.get("outcome", "attempted")),
            reward=r.get("reward", 0),
            cost=r.get("cost", 0),
            fees=r.get("fees", 0),
            net=r.get("net", 0),
            duration_seconds=r.get("duration_seconds", 0),
            error=r.get("error", ""),
            submission_url=r.get("submission_url", ""),
            notes=r.get("notes", ""),
            started_at=r.get("started_at", 0),
            completed_at=r.get("completed_at", 0),
        )
        for r in _read_all(ATTEMPTS_DB)
    ]


# --- Strategies ---

def save_strategy(strategy: Strategy) -> None:
    _append(STRATEGIES_DB, {
        "category": strategy.category,
        "platform": strategy.platform,
        "attempts": strategy.attempts,
        "successes": strategy.successes,
        "total_reward": strategy.total_reward,
        "total_cost": strategy.total_cost,
        "total_net": strategy.total_net,
        "avg_ev_per_attempt": strategy.avg_ev_per_attempt,
        "win_rate": strategy.win_rate,
        "avg_reward": strategy.avg_reward,
        "avg_net": strategy.avg_net,
    })


def load_strategies() -> list[Strategy]:
    return [
        Strategy(
            category=r.get("category", ""),
            platform=r.get("platform", ""),
            attempts=r.get("attempts", 0),
            successes=r.get("successes", 0),
            total_reward=r.get("total_reward", 0),
            total_cost=r.get("total_cost", 0),
            total_net=r.get("total_net", 0),
            avg_ev_per_attempt=r.get("avg_ev_per_attempt", 0),
            win_rate=r.get("win_rate", 0),
            avg_reward=r.get("avg_reward", 0),
            avg_net=r.get("avg_net", 0),
        )
        for r in _read_all(STRATEGIES_DB)
    ]


def get_daily_spend() -> float:
    """Total cost in the last 24 hours."""
    cutoff = time.time() - 86400
    total = 0.0
    for r in _read_all(ATTEMPTS_DB):
        if r.get("started_at", 0) > cutoff:
            total += r.get("cost", 0) + r.get("fees", 0)
    return total
