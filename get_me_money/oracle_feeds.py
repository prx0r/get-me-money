"""Oracle feeds — three distinct views of the market.

1. WORK FEED: what can I get paid to do?
2. DEMAND FEED: what are agents paying for?
3. SUPPLY FEED: what capabilities can I buy/use?

Each feed serves a different agent question.
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class WorkOpportunity:
    """Something an agent can get paid to do."""
    id: str = ""
    source: str = ""
    title: str = ""
    description: str = ""
    reward_usd: float = 0.0
    currency: str = "USDC"
    category: str = ""
    skills: list[str] = field(default_factory=list)
    deadline: str = ""
    competition: int = 0
    url: str = ""
    execution_mode: str = "agent_only"  # agent_only | human_involved
    raw: dict = field(default_factory=dict)


@dataclass
class ServiceCapability:
    """Something an agent can buy/use to do work."""
    id: str = ""
    source: str = ""
    name: str = ""
    description: str = ""
    category: str = ""
    price_per_call: float = 0.0
    currency: str = "USD"
    usage_30d: int = 0
    buyers_30d: int = 0
    url: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class DemandSignal:
    """What capabilities the market is buying."""
    capability: str = ""
    source: str = ""
    open_jobs: int = 0
    total_reward_usd: float = 0.0
    median_reward: float = 0.0
    trend_7d: float = 0.0
    trend_30d: float = 0.0


@dataclass
class IncentiveSignal:
    """Earn by being the best implementation."""
    capability: str = ""
    source: str = ""
    reward_potential: str = ""  # HIGH/MEDIUM/LOW
    competition: str = ""  # HIGH/MEDIUM/LOW
    entry_cost_usd: float = 0.0
    benchmark_available: bool = False
    score_gap: float = 0.0  # vs incumbent


@dataclass
class ResourceSignal:
    """Compute/infrastructure supply."""
    resource_type: str = ""  # GPU, CPU, TEE
    source: str = ""
    availability: int = 0
    price_per_hour: float = 0.0
    region: str = ""


@dataclass
class OpportunityRanking:
    """Vector ranking — not a single number."""
    expected_payout_usd: float = 0.0
    expected_cost_usd: float = 0.0
    expected_net_usd: float = 0.0
    wall_time_hours: float = 0.0
    human_time_minutes: float = 0.0
    capital_required_usd: float = 0.0
    p_get_paid: float = 0.0
    autonomy: str = "H0"
    confidence: float = 0.0
    skill_reuse: str = ""  # HIGH/MEDIUM/LOW
    learning_value: str = ""  # HIGH/MEDIUM/LOW
    recurring_upside: str = ""  # HIGH/MEDIUM/LOW


class OracleFeeds:
    """Three feeds from the oracle:

    1. WORK: what can I get paid to do?
    2. DEMAND: what are agents paying for?
    3. SUPPLY: what capabilities can I buy/use?
    """

    def __init__(self):
        self._db = None

    def _get_db(self):
        if self._db is not None:
            return self._db
        try:
            import sys
            sys.path.insert(0, "/root/repute")
            from oracle.store import get_db
            self._db = get_db()
            return self._db
        except Exception:
            return None

    # ─── WORK FEED ─────────────────────────────────────────────────────

    def work(self, skills: list[str] | None = None, min_reward: float = 0,
             limit: int = 50) -> list[WorkOpportunity]:
        """What can I get paid to do right now?"""
        results = []

        # Taskmarket bounties from local DB
        db = self._get_db()
        if db:
            results.extend(self._work_from_db(db, skills, min_reward, limit))

        return results[:limit]

    def _work_from_db(self, db, skills, min_reward, limit):
        query = "SELECT * FROM opportunities WHERE 1=1"
        params = []
        if min_reward > 0:
            query += " AND reward_usd >= ?"
            params.append(min_reward)
        query += " ORDER BY reward_usd DESC LIMIT ?"
        params.append(limit)

        try:
            rows = db.execute(query, params).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                opp = WorkOpportunity(
                    id=d.get("id", ""), source=d.get("source", ""),
                    title=d.get("title", ""),
                    description=d.get("description", "")[:200],
                    reward_usd=float(d.get("reward_usd", 0) or 0),
                    category=d.get("category", ""),
                    skills=[s.strip() for s in (d.get("skills") or "").split(",") if s.strip()],
                    url=d.get("url", ""),
                )
                if skills:
                    opp_skills = set(s.lower() for s in opp.skills)
                    if not opp_skills.intersection(set(s.lower() for s in skills)):
                        continue
                results.append(opp)
            return results
        except Exception:
            return []

    # ─── DEMAND FEED ───────────────────────────────────────────────────

    def demand(self, capability: str = "") -> list[DemandSignal]:
        """What are agents paying for?"""
        # Start with job-based demand
        signals = []
        db = self._get_db()
        if db:
            try:
                rows = db.execute("""
                    SELECT category, COUNT(*) as jobs, SUM(reward_usd) as total
                    FROM opportunities GROUP BY category
                """).fetchall()
                for row in rows:
                    d = dict(row)
                    signals.append(DemandSignal(
                        capability=d.get("category", ""),
                        source="taskmarket",
                        open_jobs=d.get("jobs", 0),
                        total_reward_usd=float(d.get("total", 0) or 0),
                    ))
            except Exception:
                pass
        return signals

    # ─── SUPPLY FEED ───────────────────────────────────────────────────

    def supply(self, query: str = "", limit: int = 20) -> list[ServiceCapability]:
        """What capabilities can I buy/use?"""
        results = []

        # Apify actors
        try:
            import urllib.parse, urllib.request
            url = f"https://api.apify.com/v2/store?limit={min(limit, 20)}"
            if query:
                url += f"&search={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read())
                items = raw.get("data", {}).get("items", [])
                for a in items:
                    stats = a.get("stats", {})
                    results.append(ServiceCapability(
                        id=f"apify:{a.get('username','')}/{a.get('name','')}",
                        source="apify",
                        name=a.get("title", ""),
                        category=a.get("category", "tool"),
                        usage_30d=stats.get("totalUsers30Days", 0),
                        buyers_30d=stats.get("totalUsers7D", 0),
                        url=f"https://apify.com/{a.get('username','')}/{a.get('name','')}",
                        raw=stats,
                    ))
        except Exception:
            pass

        return results[:limit]

    # ─── CAPABILITY RESOLUTION ──────────────────────────────────────────

    def resolve_capabilities(self, skills: list[str], limit: int = 5) -> list[ServiceCapability]:
        """Given skills needed, find tools that provide them."""
        results = []
        for skill in skills:
            tools = self.supply(query=skill, limit=3)
            results.extend(tools)
        # Dedup
        seen = set()
        unique = []
        for r in results:
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)
        return unique[:limit]
