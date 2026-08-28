"""Oracle client — bridges get-me-money submission loop to the oracle dataset.

Works two ways:
  1. Remote: calls oracle API (http://localhost:8788/v1/*)
  2. Embedded: imports oracle directly (same process)

The oracle provides WHAT WORK EXISTS.
The submission loop provides HOW TO WIN IT.
This client bridges the two.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class OracleOpportunity:
    """Normalized opportunity from the oracle."""
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
    """Client for the Moltwork Oracle.

    Usage:
        oracle = OracleClient()  # connects to localhost:8788
        opps = oracle.search(skills=["python", "research"], min_reward=10)
        opp = oracle.get(opportunity_id)
    """

    def __init__(self, base_url: str = "http://localhost:8788"):
        self.base_url = base_url.rstrip("/")
        self._db = None

    def _get_db(self):
        """Try to import oracle DB directly (embedded mode)."""
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

    def search(self, skills: list[str] | None = None, min_reward: float = 0,
               source: str | None = None, category: str | None = None,
               limit: int = 50) -> list[OracleOpportunity]:
        """Search opportunities from the oracle."""
        # Try embedded mode first
        db = self._get_db()
        if db:
            return self._search_db(db, skills, min_reward, source, category, limit)

        # Fall back to API
        return self._search_api(skills, min_reward, source, category, limit)

    def _search_db(self, db, skills, min_reward, source, category, limit):
        """Search directly against oracle SQLite."""
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
                    id=d.get("id", ""),
                    source=d.get("source", ""),
                    source_id=d.get("source_id", ""),
                    title=d.get("title", ""),
                    description=d.get("description", ""),
                    reward_usd=float(d.get("reward_usd", 0) or 0),
                    category=d.get("category", ""),
                    skills=self._parse_skills(d.get("skills", "")),
                    status=d.get("status", ""),
                    url=d.get("url", ""),
                    competition=int(d.get("competition", 0) or 0),
                )
                # Filter by skills if specified
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

    def _search_api(self, skills, min_reward, source, category, limit):
        """Search via REST API."""
        import urllib.request
        params = []
        if skills:
            params.append(f"skills={','.join(skills)}")
        if min_reward > 0:
            params.append(f"min_reward={min_reward}")
        if source:
            params.append(f"source={source}")
        if category:
            params.append(f"category={category}")
        params.append(f"limit={limit}")

        url = f"{self.base_url}/v1/opportunities?{'&'.join(params)}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return [OracleOpportunity(**o) for o in data.get("opportunities", [])]
        except Exception as e:
            log.warning(f"API search failed: {e}")
            return []

    def get(self, opportunity_id: str) -> OracleOpportunity | None:
        """Get a single opportunity by ID."""
        db = self._get_db()
        if db:
            try:
                row = db.execute("SELECT * FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
                if row:
                    d = dict(row)
                    return OracleOpportunity(
                        id=d.get("id", ""), source=d.get("source", ""),
                        source_id=d.get("source_id", ""), title=d.get("title", ""),
                        description=d.get("description", ""),
                        reward_usd=float(d.get("reward_usd", 0) or 0),
                        category=d.get("category", ""),
                        skills=self._parse_skills(d.get("skills", "")),
                        status=d.get("status", ""), url=d.get("url", ""),
                        competition=int(d.get("competition", 0) or 0),
                    )
            except Exception:
                pass
        return None

    def trending_skills(self, window: str = "30d", limit: int = 20) -> list[dict]:
        """Get trending skills from demand data."""
        db = self._get_db()
        if db:
            try:
                rows = db.execute("""
                    SELECT skill, SUM(reward_usd) as total_reward, COUNT(*) as opportunities
                    FROM opportunity_skills
                    JOIN opportunities ON opportunity_skills.opportunity_id = opportunities.id
                    GROUP BY skill
                    ORDER BY total_reward DESC
                    LIMIT ?
                """, (limit,)).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                pass
        return []

    def stats(self) -> dict:
        """Get oracle statistics."""
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
