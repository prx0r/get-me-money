"""Append-only JSONL economic ledger with latest-record reconciliation."""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

from get_me_money.config import ATTEMPTS_DB, OPPORTUNITIES_DB, STRATEGIES_DB
from get_me_money.models import Attempt, Opportunity, Outcome, Platform, Strategy, TaskCategory


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, default=str, separators=(",", ":")) + "\n"
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(fd, line.encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_all(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                if line.strip():
                    yield json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue


def save_opportunity(opp: Opportunity) -> None:
    d = asdict(opp)
    d["platform"] = opp.platform.value
    d["category"] = opp.category.value
    _append(OPPORTUNITIES_DB, d)


def _opp_from(r: dict) -> Opportunity:
    return Opportunity(
        id=r.get("id", ""), platform=Platform(r.get("platform", "custom")),
        external_id=r.get("external_id", ""), title=r.get("title", ""),
        description=r.get("description", ""), url=r.get("url", ""),
        reward=float(r.get("reward", 0) or 0), currency=r.get("currency", "USD"),
        category=TaskCategory(r.get("category", "unknown")), tags=list(r.get("tags", []) or []),
        posted_at=float(r.get("posted_at", 0) or 0), expires_at=float(r.get("expires_at", 0) or 0),
        competition_estimate=int(r.get("competition_estimate", 0) or 0),
        verification_strength=float(r.get("verification_strength", .5) or .5),
        payment_reliability=float(r.get("payment_reliability", .5) or .5),
        raw=dict(r.get("raw", {}) or {}), fetched_at=float(r.get("fetched_at", 0) or 0),
    )


def load_opportunities() -> list[Opportunity]:
    latest: dict[str, dict] = {}
    for r in _read_all(OPPORTUNITIES_DB):
        try:
            o = _opp_from(r)
            latest[o.fingerprint()] = r
        except (ValueError, TypeError):
            continue
    return [_opp_from(r) for r in latest.values()]


def save_attempt(a: Attempt) -> None:
    d = asdict(a)
    d["platform"] = a.platform.value
    d["outcome"] = a.outcome.value
    d["updated_at"] = time.time()
    _append(ATTEMPTS_DB, d)


def _attempt_from(r: dict) -> Attempt:
    return Attempt(
        id=r.get("id", ""), opportunity_id=r.get("opportunity_id", ""),
        platform=Platform(r.get("platform", "custom")), external_id=r.get("external_id", ""),
        title=r.get("title", ""), outcome=Outcome(r.get("outcome", "pending")),
        reward=float(r.get("reward", 0) or 0), cost=float(r.get("cost", 0) or 0),
        fees=float(r.get("fees", 0) or 0), net=float(r.get("net", 0) or 0),
        duration_seconds=float(r.get("duration_seconds", 0) or 0), error=r.get("error", ""),
        submission_url=r.get("submission_url", ""), notes=r.get("notes", ""),
        started_at=float(r.get("started_at", 0) or 0), completed_at=float(r.get("completed_at", 0) or 0),
        updated_at=float(r.get("updated_at", 0) or 0), metadata=dict(r.get("metadata", {}) or {}),
    )


def load_attempts() -> list[Attempt]:
    latest: dict[str, dict] = {}
    for r in _read_all(ATTEMPTS_DB):
        key = r.get("id")
        if key:
            latest[key] = r
    return [_attempt_from(r) for r in latest.values()]


def get_attempt(attempt_id: str) -> Attempt | None:
    return next((a for a in load_attempts() if a.id == attempt_id), None)


def save_strategy(s: Strategy) -> None:
    _append(STRATEGIES_DB, asdict(s))


def load_strategies() -> list[Strategy]:
    latest: dict[str, dict] = {}
    for r in _read_all(STRATEGIES_DB):
        latest[f"{r.get('category')}:{r.get('platform')}"] = r
    return [Strategy(**{k: r.get(k, getattr(Strategy(), k)) for k in Strategy.__dataclass_fields__}) for r in latest.values()]


def get_spend_since(cutoff: float) -> float:
    return sum(a.cost + a.fees for a in load_attempts() if a.started_at >= cutoff)


def get_daily_spend() -> float:
    return get_spend_since(time.time() - 86400)


def get_lifetime_spend() -> float:
    return sum(a.cost + a.fees for a in load_attempts())
