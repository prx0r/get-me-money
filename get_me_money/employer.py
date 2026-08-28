"""Employer mode — decompose big work into micro-bounties.

The same WorkerKit loop, inverted:
  NORMAL:    find work → do work → get paid
  EMPLOYER:  decompose work → post micro-bounties → agents compete → assemble → get paid

This enables:
  - One agent tackling a $50 bounty by splitting into 500 × $0.10 micro-tasks
  - Quality competition on each part
  - Parallel execution
  - Risk distribution (one bad part doesn't kill the whole bounty)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from get_me_money.config import Config
from get_me_money.hermes_runtime import HermesRunner
from get_me_money.jobspec import JobSpec
from get_me_money.models import Evaluation, Opportunity, Platform

log = logging.getLogger(__name__)


@dataclass
class MicroTask:
    """A decomposed sub-task of a larger bounty."""
    id: str = ""
    title: str = ""
    description: str = ""
    requirements: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)  # other micro-task IDs
    estimated_reward: float = 0.0
    skills_needed: list[str] = field(default_factory=list)


@dataclass
class Decomposition:
    """Result of decomposing a large task into micro-bounties."""
    original_task: str = ""
    micro_tasks: list[MicroTask] = field(default_factory=list)
    assembly_plan: str = ""
    total_estimated_cost: float = 0.0
    parallelizable: bool = True


async def decompose_task(
    config: Config,
    opp: Opportunity,
    max_parts: int = 10,
    min_reward_per_part: float = 0.10,
) -> Decomposition:
    """Use Hermes to decompose a large task into micro-bounties.

    The agent becomes an employer — it posts work for other agents.
    Each micro-bounty is small enough that other WorkerKit agents
    can compete on it, giving the employer the best quality per part.
    """
    prompt = f"""Decompose this task into {max_parts} independent micro-bounties.

TASK: {opp.title}
DESCRIPTION: {opp.description[:3000]}
REWARD: ${opp.reward:.2f}

Each micro-bounty should be:
- Independently completable by a different agent
- Valued at approximately ${min_reward_per_part:.2f} - ${opp.reward/max_parts:.2f} each
- Clear enough that another agent can understand and complete it

Produce ONLY a JSON object:
{{
  "micro_tasks": [
    {{
      "id": "part-1",
      "title": "short title",
      "description": "what to produce",
      "requirements": ["specific deliverable 1", "specific deliverable 2"],
      "depends_on": [],
      "estimated_reward": 0.50,
      "skills_needed": ["python", "research"]
    }}
  ],
  "assembly_plan": "how to combine the parts into the final submission",
  "parallelizable": true
}}

Rules:
- Prefer independent parts (depends_on = []) for parallelism
- Each part must produce a concrete deliverable (not "research" but "list of 5 competitors with URLs")
- Total estimated reward should not exceed the original bounty
- Return ONLY the JSON object"""

    opp_copy = Opportunity(
        id=opp.id, platform=Platform.TASKMARKET, external_id=opp.external_id,
        title=f"Decompose: {opp.title}", description=prompt,
        category=opp.category, reward=opp.reward, currency=opp.currency,
    )
    ev = Evaluation(opportunity_id=opp.id, probability_of_success=0.5, ev_cash=0, estimated_cost=0.01)
    runner = HermesRunner(config)
    result = await runner.run(opp_copy, ev)

    # Parse response
    content = result.get("content", "")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        import re
        m = re.search(r"\{.*\}", content, re.S)
        data = json.loads(m.group(0)) if m else {}

    decomp = Decomposition(
        original_task=opp.title,
        assembly_plan=data.get("assembly_plan", ""),
        parallelizable=data.get("parallelizable", True),
    )

    for mt in data.get("micro_tasks", []):
        decomp.micro_tasks.append(MicroTask(
            id=mt.get("id", ""),
            title=mt.get("title", ""),
            description=mt.get("description", ""),
            requirements=mt.get("requirements", []),
            depends_on=mt.get("depends_on", []),
            estimated_reward=float(mt.get("estimated_reward", 0)),
            skills_needed=mt.get("skills_needed", []),
        ))

    decomp.total_estimated_cost = sum(mt.estimated_reward for mt in decomp.micro_tasks)
    return decomp


async def find_micro_bounties(
    config: Config,
    max_reward_per_part: float = 5.0,
    skills: list[str] | None = None,
) -> list[dict]:
    """Find micro-bounties that other agents might post.

    In the future, this queries the oracle for posted micro-bounties.
    For now, it scans existing platforms for small tasks.
    """
    from get_me_money.ledger import load_opportunities

    opps = load_opportunities()
    results = []
    for o in opps:
        if o.reward <= max_reward_per_part:
            if skills:
                opp_skills = set(s.lower() for s in (o.tags or []))
                if not opp_skills.intersection(set(s.lower() for s in skills)):
                    continue
            results.append({
                "id": o.external_id,
                "title": o.title[:60],
                "reward": o.reward,
                "platform": o.platform.value,
                "category": o.category.value,
            })

    return sorted(results, key=lambda x: x["reward"], reverse=True)[:20]


def format_micro_bounty_post(task: MicroTask, parent_bounty: str = "") -> str:
    """Format a micro-task for posting to a marketplace."""
    lines = [
        f"# {task.title}",
        "",
        f"**Reward:** ${task.estimated_reward:.2f}",
    ]
    if parent_bounty:
        lines.append(f"**Parent bounty:** {parent_bounty}")
    lines.extend([
        "",
        "## Description",
        task.description,
        "",
        "## Requirements",
    ])
    for r in task.requirements:
        lines.append(f"- {r}")

    if task.skills_needed:
        lines.extend(["", "## Skills needed", ", ".join(task.skills_needed)])

    if task.depends_on:
        lines.extend(["", "## Depends on", ", ".join(task.depends_on)])

    lines.extend([
        "",
        "## Deliverable",
        "Write your submission to SUBMISSION.md in the current directory.",
    ])

    return "\n".join(lines)
