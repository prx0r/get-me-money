"""Capability acquisition layer — assembles the right toolchain for each job.

Given a job brief, determines required capabilities, checks what's already
available, searches for missing skills, security-audits them, and builds
a job-specific Hermes profile.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from get_me_money.models import Opportunity, TaskCategory

log = logging.getLogger(__name__)

# Skills we already have (Hermes built-ins + known good)
BUILTIN_SKILLS = {
    "github-repo-management",
    "github-issue-to-pr",
    "github-code-review",
    "github-pr-workflow",
    "github-auth",
    "codebase-inspection",
    "web_search",
    "web_extract",
    "plan",
    "file-creator",
    "screen-capture",
    "browser-tool",
}

# Curated skill bundles by job category
SKILL_BUNDLES: dict[TaskCategory, list[str]] = {
    TaskCategory.CODE_FIX: [
        "github-repo-management",
        "github-issue-to-pr",
        "superpowers",
        "mp-diagnose",
        "mp-tdd",
        "mp-code-review",
        "github-pr-workflow",
    ],
    TaskCategory.CODE_FEATURE: [
        "github-repo-management",
        "github-issue-to-pr",
        "superpowers",
        "mp-implement",
        "mp-tdd",
        "mp-code-review",
        "github-pr-workflow",
    ],
    TaskCategory.RESEARCH: [
        "mp-research",
        "web_search",
        "web_extract",
        "knowledge-work-data",
    ],
    TaskCategory.DATA_EXTRACTION: [
        "mp-research",
        "web_search",
        "web_extract",
        "knowledge-work-data",
    ],
    TaskCategory.CONTENT: [
        "mp-research",
        "web_search",
        "file-creator",
    ],
    TaskCategory.API_WORK: [
        "superpowers",
        "mp-implement",
        "mp-tdd",
    ],
    TaskCategory.DESIGN: [
        "superpowers",
        "mp-implement",
        "design-taste-frontend",
    ],
    TaskCategory.TESTING: [
        "mp-tdd",
        "mp-diagnose",
    ],
    TaskCategory.DOCUMENTATION: [
        "mp-research",
        "file-creator",
    ],
}

# Known good external skills (SkillMake + verified sources)
TRUSTED_SKILLS: dict[str, dict[str, str]] = {
    "superpowers": {"source": "skillmake", "desc": "brainstorm → plan → TDD → build → review"},
    "mp-research": {"source": "skillmake", "desc": "structured research workflow"},
    "mp-diagnose": {"source": "skillmake", "desc": "understand/debug code"},
    "mp-implement": {"source": "skillmake", "desc": "build from specification"},
    "mp-tdd": {"source": "skillmake", "desc": "test-first implementation"},
    "mp-code-review": {"source": "skillmake", "desc": "review before submission"},
    "mp-wayfinder": {"source": "skillmake", "desc": "huge/complex task decomposition"},
    "playwright-skill": {"source": "skillmake", "desc": "browser acceptance testing"},
    "prospecting": {"source": "skillmake", "desc": "prospect/company research"},
    "competitors": {"source": "skillmake", "desc": "competitive research"},
    "competitor-profiling": {"source": "skillmake", "desc": "deep competitor analysis"},
    "wrangler": {"source": "skillmake", "desc": "Cloudflare deployment"},
    "design-taste-frontend": {"source": "skillmake", "desc": "frontend design quality"},
    "github-project-triage": {"source": "skillmake", "desc": "GitHub issue triage"},
    "github-deep-review": {"source": "skillmake", "desc": "deep GitHub investigation"},
}


@dataclass
class CapabilityGap:
    """What a job needs vs what we have."""
    required: list[str] = field(default_factory=list)
    already_available: list[str] = field(default_factory=list)
    need_to_acquire: list[str] = field(default_factory=list)
    untrusted: list[str] = field(default_factory=list)


@dataclass
class SkillAcquisition:
    """A skill to install for a job."""
    name: str
    source: str
    reason: str
    trusted: bool = True
    security_review: str = "pending"


@dataclass
class JobPlan:
    """Complete plan for executing a job."""
    opportunity: Opportunity | None = None
    capabilities: CapabilityGap | None = None
    acquisitions: list[SkillAcquisition] = field(default_factory=list)
    workspace: str = ""
    hermes_home: str = ""
    skills_installed: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_duration: float = 0.0


class CapabilityBroker:
    """Assembles the right temporary toolchain for each job.

    Flow:
    1. Parse job requirements
    2. Match to skill bundles
    3. Check what's already available
    4. Identify gaps
    5. Search for missing skills (trusted sources only)
    6. Security review
    7. Build job-specific Hermes profile
    """

    def __init__(self, jobs_dir: Path, hermes_binary: str = "hermes"):
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.hermes_binary = hermes_binary

    def analyze_requirements(self, opp: Opportunity) -> CapabilityGap:
        """Determine what capabilities a job needs."""
        # Start with the category bundle
        bundle = list(SKILL_BUNDLES.get(opp.category, []))

        # Add skills based on title/description keywords
        text = (opp.title + " " + opp.description).lower()
        extra = self._keyword_skills(text)
        bundle.extend(extra)

        # Deduplicate while preserving order
        seen = set()
        required = []
        for s in bundle:
            if s not in seen:
                seen.add(s)
                required.append(s)

        # Split into available vs needed
        available = [s for s in required if s in BUILTIN_SKILLS]
        need = [s for s in required if s not in BUILTIN_SKILLS]

        return CapabilityGap(
            required=required,
            already_available=available,
            need_to_acquire=need,
        )

    def _keyword_skills(self, text: str) -> list[str]:
        """Add skills based on job description keywords."""
        skills = []
        if any(w in text for w in ["next.js", "nextjs", "react", "frontend"]):
            skills.extend(["design-taste-frontend", "playwright-skill"])
        if any(w in text for w in ["deploy", "cloudflare", "vercel", "hosting"]):
            skills.append("wrangler")
        if any(w in text for w in ["three.js", "3d", "webgl", "visualization"]):
            skills.append("playwright-skill")
        if any(w in text for w in ["browser", "scrape", "crawl", "screenshot"]):
            skills.append("playwright-skill")
        if any(w in text for w in ["investor", "company", "prospect", "startup"]):
            skills.extend(["prospecting", "competitor-profiling"])
        if any(w in text for w in ["competitor", "market", "landscape"]):
            skills.extend(["competitors", "competitor-profiling"])
        if any(w in text for w in ["complex", "large", "multiple", "decompose"]):
            skills.append("mp-wayfinder")
        return skills

    def plan_acquisitions(self, gap: CapabilityGap) -> list[SkillAcquisition]:
        """Determine which skills to acquire."""
        acquisitions = []
        for skill in gap.need_to_acquire:
            info = TRUSTED_SKILLS.get(skill)
            if info:
                acquisitions.append(SkillAcquisition(
                    name=skill,
                    source=info["source"],
                    reason=info["desc"],
                    trusted=True,
                ))
            else:
                # Unknown skill — flag for security review
                acquisitions.append(SkillAcquisition(
                    name=skill,
                    source="unknown",
                    reason="not in trusted catalog",
                    trusted=False,
                    security_review="required",
                ))
        return acquisitions

    async def build_job_profile(self, opp: Opportunity) -> JobPlan:
        """Build a complete job plan with isolated Hermes profile."""
        gap = self.analyze_requirements(opp)
        acquisitions = self.plan_acquisitions(gap)

        # Create job workspace
        job_id = f"{opp.platform.value}-{opp.id}"
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        hermes_home = job_dir / "hermes-home"
        workspace = job_dir / "workspace"
        artifacts = job_dir / "artifacts"
        plan_dir = job_dir / "plan"
        security = job_dir / "security"

        for d in (hermes_home, workspace, artifacts, plan_dir, security):
            d.mkdir(exist_ok=True)

        # Write job manifest
        manifest = {
            "job_id": job_id,
            "platform": opp.platform.value,
            "external_id": opp.external_id,
            "title": opp.title,
            "reward": opp.reward,
            "currency": opp.currency,
            "category": opp.category.value,
            "capabilities_required": gap.required,
            "capabilities_available": gap.already_available,
            "capabilities_acquiring": [a.name for a in acquisitions],
            "skills_trusted": [a.name for a in acquisitions if a.trusted],
            "skills_untrusted": [a.name for a in acquisitions if not a.trusted],
        }
        (job_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        return JobPlan(
            opportunity=opp,
            capabilities=gap,
            acquisitions=acquisitions,
            workspace=str(workspace),
            hermes_home=str(hermes_home),
            estimated_cost=self._estimate_cost(opp, acquisitions),
            estimated_duration=self._estimate_duration(opp),
        )

    def _estimate_cost(self, opp: Opportunity, acquisitions: list[SkillAcquisition]) -> float:
        """Estimate compute cost for the job."""
        from get_me_money.evaluator import CATEGORY_HOURS, COST_PER_1K_TOKENS, TOKENS_PER_HOUR, HTTP_COST_PER_HOUR
        hours = CATEGORY_HOURS.get(opp.category, 1.5)
        # Skill installation adds overhead
        skill_overhead = len(acquisitions) * 0.005
        return (hours * TOKENS_PER_HOUR / 1000.0 * COST_PER_1K_TOKENS) + (hours * HTTP_COST_PER_HOUR) + skill_overhead

    def _estimate_duration(self, opp: Opportunity) -> float:
        """Estimate duration in seconds."""
        from get_me_money.evaluator import CATEGORY_HOURS
        hours = CATEGORY_HOURS.get(opp.category, 1.5)
        return hours * 3600

    def record_skill_performance(self, job_id: str, skills: list[str],
                                  won: bool, cost: float, reward: float) -> None:
        """Record how well a skill combination performed."""
        perf_file = self.jobs_dir / "skill-performance.jsonl"
        record = {
            "job_id": job_id,
            "skills": sorted(skills),
            "won": won,
            "cost": cost,
            "reward": reward,
            "net": reward - cost,
        }
        with open(perf_file, "a") as f:
            f.write(json.dumps(record) + "\n")

    def best_bundle(self, category: TaskCategory) -> list[str]:
        """Get the historically best-performing skill bundle for a category."""
        perf_file = self.jobs_dir / "skill-performance.jsonl"
        if not perf_file.exists():
            return SKILL_BUNDLES.get(category, [])

        # Aggregate performance by skill combination
        combos: dict[str, dict] = {}
        for line in perf_file.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = json.dumps(r["skills"])
            if key not in combos:
                combos[key] = {"wins": 0, "total": 0, "total_net": 0.0}
            combos[key]["total"] += 1
            if r.get("won"):
                combos[key]["wins"] += 1
            combos[key]["total_net"] += r.get("net", 0)

        # Find best combo with at least 2 attempts
        best_key = None
        best_score = -1
        for key, stats in combos.items():
            if stats["total"] < 2:
                continue
            win_rate = stats["wins"] / stats["total"]
            avg_net = stats["total_net"] / stats["total"]
            score = win_rate * 0.6 + (avg_net / 10.0) * 0.4  # normalize net
            if score > best_score:
                best_score = score
                best_key = key

        if best_key:
            return json.loads(best_key)
        return SKILL_BUNDLES.get(category, [])
