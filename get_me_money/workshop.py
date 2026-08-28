"""Workshop — the composition layer where agents build things.

Theme: Blueprint → Build → Artifact

A worker picks up a blueprint, gathers parts from the Moltwork economy,
assembles something, and produces an artifact.

The workshop is where:
  - blueprints define what to build
  - parts are sourced from other agents
  - skills are applied
  - artifacts emerge
  - everything is recorded
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Part:
    """A reusable input from the Moltwork economy."""
    id: str = ""
    name: str = ""
    type: str = ""  # "dataset", "skill", "service", "template", "evidence"
    source: str = ""  # worker_id or platform
    cost: float = 0.0
    evidence: str = ""  # "used in 2841 WorkRuns, $18k downstream revenue"


@dataclass
class Blueprint:
    """A reusable composition strategy — what to build and how."""
    id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""  # "research", "code", "design", "analysis"

    # What this blueprint produces
    output_type: str = ""  # "report", "dataset", "code", "service"

    # What it needs
    required_parts: list[str] = field(default_factory=list)  # part types
    required_skills: list[str] = field(default_factory=list)

    # How it works
    steps: list[str] = field(default_factory=list)

    # Economics
    estimated_cost: float = 0.0
    historical_acceptance: float = 0.0
    uses: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_prompt(self) -> str:
        lines = [f"# Blueprint: {self.name}", ""]
        lines.append(f"**Category:** {self.category}")
        lines.append(f"**Output:** {self.output_type}")
        lines.append(f"**Estimated cost:** ${self.estimated_cost:.2f}")
        lines.append("")
        if self.description:
            lines.append(f"## Description\n{self.description}")
        if self.required_parts:
            lines.append(f"\n## Required Parts\n" + "\n".join(f"- {p}" for p in self.required_parts))
        if self.required_skills:
            lines.append(f"\n## Skills\n" + ", ".join(self.required_skills))
        if self.steps:
            lines.append(f"\n## Steps\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(self.steps)))
        return "\n".join(lines)


@dataclass
class Worker:
    """A named worker with a specific build configuration."""
    id: str = ""
    name: str = ""
    description: str = ""

    # Build
    runtime: str = "hermes"
    model: str = "mimo-v2.5"
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    blueprint: str = ""  # default blueprint this worker uses

    # Stats
    jobs_completed: int = 0
    jobs_accepted: int = 0
    earnings: float = 0.0
    avg_quality: float = 0.0

    # Visual
    color: str = "#4a9eff"  # for three.js
    avatar: str = ""  # emoji or icon

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Starter Blueprints ─────────────────────────────────────────────

BLUEPRINTS = {
    "competitor-intel": Blueprint(
        id="competitor-intel",
        name="Competitive Intelligence Report",
        description="Research competitors, analyze positioning, identify gaps",
        category="research",
        output_type="report",
        required_parts=["company-list", "web-search", "funding-data"],
        required_skills=["research", "analysis", "writing"],
        steps=[
            "Research each competitor",
            "Analyze their positioning",
            "Identify market gaps",
            "Write structured report",
            "Verify claims with sources",
        ],
        estimated_cost=0.41,
        historical_acceptance=0.82,
    ),
    "market-report": Blueprint(
        id="market-report",
        name="Market Research Report",
        description="Size market, identify players, analyze trends",
        category="research",
        output_type="report",
        required_parts=["web-search", "industry-data"],
        required_skills=["research", "analysis"],
        steps=[
            "Define market boundaries",
            "Find key players",
            "Estimate market size",
            "Analyze trends and drivers",
            "Write report with sources",
        ],
        estimated_cost=0.35,
        historical_acceptance=0.78,
    ),
    "code-review": Blueprint(
        id="code-review",
        name="Code Review & Audit",
        description="Review code for quality, security, and best practices",
        category="code",
        output_type="report",
        required_parts=["codebase"],
        required_skills=["coding", "security", "review"],
        steps=[
            "Read and understand code",
            "Check for bugs and security issues",
            "Evaluate code quality",
            "Write review with recommendations",
        ],
        estimated_cost=0.25,
        historical_acceptance=0.85,
    ),
    "data-extraction": Blueprint(
        id="data-extraction",
        name="Structured Data Extraction",
        description="Extract structured data from unstructured sources",
        category="analysis",
        output_type="dataset",
        required_parts=["source-data", "schema"],
        required_skills=["extraction", "parsing"],
        steps=[
            "Parse source material",
            "Extract relevant fields",
            "Validate against schema",
            "Output structured dataset",
        ],
        estimated_cost=0.15,
        historical_acceptance=0.90,
    ),
}

# ─── Starter Workers ─────────────────────────────────────────────────

WORKERS = {
    "scout": Worker(
        id="scout",
        name="Scout",
        description="Research specialist — finds and verifies information",
        runtime="hermes",
        model="mimo-v2.5",
        skills=["research", "web-search", "verification", "analysis"],
        tools=["browser", "search"],
        blueprint="competitor-intel",
        color="#4a9eff",
        avatar="🔍",
    ),
    "forge": Worker(
        id="forge",
        name="Forge",
        description="Code specialist — builds and reviews software",
        runtime="hermes",
        model="mimo-v2.5",
        skills=["coding", "testing", "review", "deployment"],
        tools=["github", "terminal", "browser"],
        blueprint="code-review",
        color="#ff6b4a",
        avatar="⚒️",
    ),
    "oracle": Worker(
        id="oracle",
        name="Oracle",
        description="Analysis specialist — processes data and finds patterns",
        runtime="hermes",
        model="mimo-v2.5",
        skills=["analysis", "extraction", "parsing", "visualization"],
        tools=["data", "spreadsheet"],
        blueprint="data-extraction",
        color="#4aff8b",
        avatar="🔮",
    ),
    "relay": Worker(
        id="relay",
        name="Relay",
        description="Operator — connects systems and automates workflows",
        runtime="hermes",
        model="mimo-v2.5",
        skills=["api", "automation", "integration", "monitoring"],
        tools=["api", "browser", "terminal"],
        blueprint="market-report",
        color="#ffb84a",
        avatar="⚡",
    ),
}


def get_blueprint(blueprint_id: str) -> Blueprint | None:
    return BLUEPRINTS.get(blueprint_id)


def get_worker(worker_id: str) -> Worker | None:
    return WORKERS.get(worker_id)


def list_blueprints(category: str = "") -> list[Blueprint]:
    bps = list(BLUEPRINTS.values())
    if category:
        bps = [b for b in bps if b.category == category]
    return bps


def list_workers() -> list[Worker]:
    return list(WORKERS.values())
