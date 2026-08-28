"""Oracle client — unified search across all sources.

Queries:
  - Local oracle DB (Taskmarket, etc.)
  - Apify Store (51K+ tools with real usage data)
  - Future: any adapter that implements search()

The oracle provides WHAT WORK EXISTS.
The submission loop provides HOW TO WIN IT.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class OracleOpportunity:
    """Normalized opportunity from any source."""
    id: str = ""
    source: str = ""
    source_id: str = ""
    title: str = ""
    description: str = ""
    reward_usd: float = 0.0
    category: str = ""
    skills: list[str] = field(default_factory=list)
    status: str = ""
    url: str = ""
    competition: int = 0
    deadline: str = ""
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "source": self.source, "source_id": self.source_id,
            "title": self.title, "description": self.description,
            "reward_usd": self.reward_usd, "category": self.category,
            "skills": self.skills, "status": self.status, "url": self.url,
            "competition": self.competition, "deadline": self.deadline,
        }


class OracleClient:
    """Unified oracle: queries local DB + live adapters.

    Usage:
        oracle = OracleClient()
        opps = oracle.search(skills=["python"], min_reward=10)
        # Returns both Taskmarket bounties AND Apify tools
    """

    def __init__(self, base_url: str = "http://localhost:8788"):
        self.base_url = base_url.rstrip("/")
        self._db = None
        self._apify = None

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

    def _get_apify(self):
        if self._apify is not None:
            return self._apify
        try:
            from get_me_money.markets.apify import ApifyAdapter
            self._apify = ApifyAdapter()
            return self._apify
        except Exception:
            return None

    async def search(self, skills: list[str] | None = None, min_reward: float = 0,
               source: str | None = None, category: str | None = None,
               limit: int = 50) -> list[OracleOpportunity]:
        """Search WORK FEED — opportunities to earn money."""
        return await self._search(skills, min_reward, source, category, limit,
                                  sources=["taskmarket", "algora", "bountybook", "superteam"])

    def search_sync(self, skills: list[str] | None = None, min_reward: float = 0,
               source: str | None = None, category: str | None = None,
               limit: int = 50) -> list[OracleOpportunity]:
        """Synchronous WORK FEED search."""
        return self._search_sync(skills, min_reward, source, category, limit,
                                 sources=["taskmarket", "algora", "bountybook", "superteam"])

    async def search_tools(self, query: str = "", limit: int = 20) -> list[OracleOpportunity]:
        """Search TOOL FEED — Apify actors, MCPs, APIs to use."""
        results = []
        apify = self._get_apify()
        if apify:
            try:
                apify_results = await self._search_apify(apify, [], limit)
                results.extend(apify_results)
            except Exception as e:
                log.warning(f"Apify search failed: {e}")
        return results[:limit]

    def search_tools_sync(self, query: str = "", limit: int = 20) -> list[OracleOpportunity]:
        """Synchronous TOOL FEED search."""
        results = []
        try:
            from get_me_money.markets.apify import ApifyAdapter
            import urllib.parse, urllib.request
            apify = ApifyAdapter()
            url = f"{apify.base}/store?limit={min(limit, 20)}"
            if query:
                url += f"&search={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers=apify._headers())
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read())
                items = raw.get("data", {}).get("items", [])
                for a in items:
                    results.append(OracleOpportunity(
                        id=f"apify:{a.get('username','')}/{a.get('name','')}",
                        source="apify", source_id=a.get("name", ""),
                        title=a.get("title", ""), reward_usd=0,
                        category="tool", skills=[], status="active",
                        url=f"https://apify.com/{a.get('username','')}/{a.get('name','')}",
                        raw=a.get("stats", {}),
                    ))
        except Exception:
            pass
        return results[:limit]

    async def _search(self, skills, min_reward, source, category, limit, sources=None):
        results = []
        db = self._get_db()
        if db:
            results.extend(self._search_db(db, skills, min_reward, source, category, limit))
        return self._dedup(results)[:limit]

    def _search_sync(self, skills, min_reward, source, category, limit, sources=None):
        results = []
        db = self._get_db()
        if db:
            results.extend(self._search_db(db, skills, min_reward, source, category, limit))
        return self._dedup(results)[:limit]

    async def _search_apify(self, apify, skills, limit) -> list[OracleOpportunity]:
        """Search Apify Store for tools."""
        query = " ".join(skills) if skills else ""
        results = await apify.search(query, limit=min(limit, 20))
        return [
            OracleOpportunity(
                id=f"apify:{r.listing_id}",
                source="apify", source_id=r.listing_id,
                title=r.title, reward_usd=0,
                category=r.stats.get("category", "tool"),
                skills=skills or [], status="active",
                url=f"https://apify.com/{r.listing_id}",
                raw=r.stats,
            )
            for r in results
        ]

    @staticmethod
    def _dedup(results):
        seen = set()
        unique = []
        for r in results:
            key = r.title.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    def _search_db(self, db, skills, min_reward, source, category, limit):
        query = "SELECT * FROM opportunities WHERE 1=1"
        params = []
        if min_reward > 0:
            query += " AND reward_usd >= ?"
            params.append(min_reward)
        if source:
            query += " AND source = ?"
            params.append(source)
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY reward_usd DESC LIMIT ?"
        params.append(limit)

        try:
            rows = db.execute(query, params).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                opp = OracleOpportunity(
                    id=d.get("id", ""), source=d.get("source", ""),
                    source_id=d.get("source_id", ""), title=d.get("title", ""),
                    description=d.get("description", ""),
                    reward_usd=float(d.get("reward_usd", 0) or 0),
                    category=d.get("category", ""),
                    skills=self._parse_skills(d.get("skills", "")),
                    status=d.get("status", ""), url=d.get("url", ""),
                    competition=int(d.get("competition", 0) or 0),
                )
                if skills:
                    opp_skills = set(s.lower() for s in opp.skills)
                    query_skills = set(s.lower() for s in skills)
                    if not opp_skills.intersection(query_skills):
                        continue
                results.append(opp)
            return results
        except Exception as e:
            log.warning(f"DB search failed: {e}")
            return []

    def trending_skills(self, window: str = "30d", limit: int = 20) -> list[dict]:
        db = self._get_db()
        if db:
            try:
                rows = db.execute("""
                    SELECT skill, SUM(reward_usd) as total_reward, COUNT(*) as opportunities
                    FROM opportunity_skills
                    JOIN opportunities ON opportunity_skills.opportunity_id = opportunities.id
                    GROUP BY skill ORDER BY total_reward DESC LIMIT ?
                """, (limit,)).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                pass
        return []

    def stats(self) -> dict:
        db = self._get_db()
        if db:
            try:
                total = db.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
                active = db.execute("SELECT COUNT(*) FROM opportunities WHERE status='open'").fetchone()[0]
                total_reward = db.execute("SELECT SUM(reward_usd) FROM opportunities").fetchone()[0] or 0
                return {"total": total, "active": active, "total_reward_usd": total_reward}
            except Exception:
                pass
        return {}

    @staticmethod
    def _parse_skills(skills_str: str) -> list[str]:
        if not skills_str:
            return []
        return [s.strip() for s in skills_str.split(",") if s.strip()]
