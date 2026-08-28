"""WorkerConfig — the sellable unit of specialization.

A WorkerConfig is a complete configuration that turns a general WorkerKit
into a specialist worker. It's what gets sold, shared, or forked.

Config = Factory + Skills + Markets + Quality + Budget

This is the expansion pack model:
  WorkerKit (core engine)
    + WorkerConfig (specialist overlay)
    = Specialist Worker (ready to earn)
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class WorkerConfig:
    """A complete specialist worker configuration.

    This is the sellable unit. Someone buys this config,
    their agent installs it, and becomes a specialist.
    """
    id: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    # What this worker does
    factory: str = ""  # which factory to use ("report", "app", "mcp", etc.)
    specialty: str = ""  # "research", "code", "design", "data", "automation"

    # Skills and capabilities
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    methodology: str = ""  # "superpowers", "tdd", "research-first", etc.

    # Market targeting
    primary_markets: list[str] = field(default_factory=list)  # where to sell
    secondary_markets: list[str] = field(default_factory=list)  # where to distribute

    # Quality and budget
    min_judge_score: float = 0.6
    max_candidates: int = 1
    max_revisions: int = 1
    max_cost_per_job: float = 5.0
    min_reward: float = 1.0

    # Pricing (if sold as a config)
    price: float = 0.0
    license: str = "derivative-commercial"

    # Evidence
    uses: int = 0
    avg_quality: float = 0.0
    avg_earnings: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_prompt(self) -> str:
        """Generate a system prompt for this worker config."""
        lines = [f"# {self.name} Worker"]
        lines.append(f"\nYou are a {self.specialty} specialist.")
        lines.append(f"\n## Skills\n{', '.join(self.skills)}")
        lines.append(f"\n## Tools\n{', '.join(self.tools)}")
        if self.methodology:
            lines.append(f"\n## Methodology\n{self.methodology}")
        lines.append(f"\n## Quality Threshold\nMinimum judge score: {self.min_judge_score}")
        lines.append(f"\n## Markets\nPrimary: {', '.join(self.primary_markets)}")
        if self.secondary_markets:
            lines.append(f"Secondary: {', '.join(self.secondary_markets)}")
        return "\n".join(lines)

    def content_hash(self) -> str:
        raw = json.dumps({
            "name": self.name, "factory": self.factory,
            "skills": self.skills, "tools": self.tools,
            "primary_markets": self.primary_markets,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        (path / "config.json").write_text(json.dumps(self.to_dict(), indent=2))
        (path / "prompt.md").write_text(self.to_prompt())

    @classmethod
    def load(cls, path: Path) -> WorkerConfig:
        data = json.loads((path / "config.json").read_text())
        config = cls()
        for k, v in data.items():
            if hasattr(config, k):
                setattr(config, k, v)
        return config


# ─── Starter Configs ─────────────────────────────────────────────────

CONFIGS = {
    "researcher": WorkerConfig(
        id="researcher",
        name="Research Analyst",
        version="1.0.0",
        description="Finds, verifies, and synthesizes information into reports",
        factory="report",
        specialty="research",
        skills=["web-research", "source-verification", "competitive-analysis", "citation-checking", "report-writing"],
        tools=["browser", "search", "web-scraping"],
        methodology="evidence-before-claims, cite sources, verify facts",
        primary_markets=["moltwork", "gumroad", "aws_market"],
        secondary_markets=["etsy", "itchio"],
        min_judge_score=0.7,
        max_cost_per_job=2.0,
        min_reward=5.0,
        price=0.0,
    ),
    "builder": WorkerConfig(
        id="builder",
        name="Software Builder",
        version="1.0.0",
        description="Builds, tests, and deploys software products",
        factory="app",
        specialty="code",
        skills=["coding", "testing", "code-review", "deployment", "documentation"],
        tools=["github", "terminal", "browser"],
        methodology="tdd, code review, security-first",
        primary_markets=["github_market", "apple", "google_play", "itchio"],
        secondary_markets=["aws_market", "gumroad"],
        min_judge_score=0.75,
        max_cost_per_job=3.0,
        min_reward=10.0,
        price=0.0,
    ),
    "operator": WorkerConfig(
        id="operator",
        name="Automation Operator",
        version="1.0.0",
        description="Connects systems, automates workflows, manages APIs",
        factory="mcp",
        specialty="automation",
        skills=["api-integration", "workflow-automation", "data-pipeline", "monitoring", "documentation"],
        tools=["api", "terminal", "browser"],
        methodology="idempotent, observable, failure-tolerant",
        primary_markets=["apify", "aws_market", "github_market"],
        secondary_markets=["moltwork", "gumroad"],
        min_judge_score=0.65,
        max_cost_per_job=1.5,
        min_reward=3.0,
        price=0.0,
    ),
}


def get_config(name: str) -> WorkerConfig | None:
    return CONFIGS.get(name)


def list_configs() -> list[WorkerConfig]:
    return list(CONFIGS.values())
