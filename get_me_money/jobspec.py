"""JobSpec: structured task contract from raw opportunity description.

Replaces brittle category/bundle matching with explicit requirements,
scoring criteria, and rejection conditions extracted from the task brief.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class JobSpec:
    """Structured representation of what a task actually requires."""
    objective: str = ""
    hard_requirements: list[str] = field(default_factory=list)
    scoring: dict[str, float] = field(default_factory=dict)
    tie_breakers: list[str] = field(default_factory=list)
    automatic_rejection: list[str] = field(default_factory=list)
    competition: dict = field(default_factory=dict)
    evidence_required: list[str] = field(default_factory=list)
    deliverable_format: str = ""  # "markdown_files", "code", "report", etc.
    deadline: str = ""
    source_title: str = ""
    source_description: str = ""
    raw_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "hard_requirements": self.hard_requirements,
            "scoring": self.scoring,
            "tie_breakers": self.tie_breakers,
            "automatic_rejection": self.automatic_rejection,
            "competition": self.competition,
            "evidence_required": self.evidence_required,
            "deliverable_format": self.deliverable_format,
            "deadline": self.deadline,
            "source_title": self.source_title,
        }

    def to_prompt(self) -> str:
        """Format as a structured prompt for Hermes."""
        lines = [f"# JOB SPECIFICATION"]
        lines.append(f"\n## Objective\n{self.objective}")
        if self.hard_requirements:
            lines.append(f"\n## Hard Requirements (MUST satisfy ALL)")
            for i, r in enumerate(self.hard_requirements, 1):
                lines.append(f"{i}. {r}")
        if self.scoring:
            lines.append(f"\n## Scoring Criteria")
            for k, v in self.scoring.items():
                lines.append(f"- {k}: {v*100:.0f}%")
        if self.automatic_rejection:
            lines.append(f"\n## Automatic Rejection (ANY of these = fail)")
            for r in self.automatic_rejection:
                lines.append(f"- {r}")
        if self.evidence_required:
            lines.append(f"\n## Evidence Required")
            for e in self.evidence_required:
                lines.append(f"- {e}")
        if self.deliverable_format:
            lines.append(f"\n## Deliverable Format\n{self.deliverable_format}")
        if self.competition:
            lines.append(f"\n## Competition")
            for k, v in self.competition.items():
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)


@dataclass
class WinPlan:
    """Strategy for how to win a task given its JobSpec."""
    entry_decision: str = ""  # "enter" or "skip" with reason
    differentiation: str = ""  # what makes our submission stand out
    risk_factors: list[str] = field(default_factory=list)
    estimated_effort_hours: float = 0.0
    candidate_count: int = 1
    revision_rounds: int = 1
    key_criteria: list[str] = field(default_factory=list)  # highest-leverage criteria

    def to_dict(self) -> dict:
        return {
            "entry_decision": self.entry_decision,
            "differentiation": self.differentiation,
            "risk_factors": self.risk_factors,
            "estimated_effort_hours": self.estimated_effort_hours,
            "candidate_count": self.candidate_count,
            "revision_rounds": self.revision_rounds,
            "key_criteria": self.key_criteria,
        }

    def to_prompt(self) -> str:
        lines = ["# WIN PLAN"]
        lines.append(f"\n## Entry Decision\n{self.entry_decision}")
        if self.differentiation:
            lines.append(f"\n## Differentiation Strategy\n{self.differentiation}")
        if self.key_criteria:
            lines.append(f"\n## Key Criteria (highest leverage)")
            for c in self.key_criteria:
                lines.append(f"- {c}")
        if self.risk_factors:
            lines.append(f"\n## Risk Factors")
            for r in self.risk_factors:
                lines.append(f"- {r}")
        lines.append(f"\n## Config")
        lines.append(f"- Candidates: {self.candidate_count}")
        lines.append(f"- Revision rounds: {self.revision_rounds}")
        lines.append(f"- Estimated effort: {self.estimated_effort_hours:.1f}h")
        return "\n".join(lines)


def parse_jobspec_from_hermes(text: str) -> JobSpec:
    """Parse a JobSpec from hermes response text (JSON block)."""
    # Try to find JSON in the response
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

    return JobSpec(
        objective=data.get("objective", ""),
        hard_requirements=data.get("hard_requirements", []),
        scoring=data.get("scoring", {}),
        tie_breakers=data.get("tie_breakers", []),
        automatic_rejection=data.get("automatic_rejection", []),
        competition=data.get("competition", {}),
        evidence_required=data.get("evidence_required", []),
        deliverable_format=data.get("deliverable_format", ""),
        deadline=data.get("deadline", ""),
    )


def parse_winplan_from_hermes(text: str) -> WinPlan:
    """Parse a WinPlan from hermes response text (JSON block)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

    return WinPlan(
        entry_decision=data.get("entry_decision", ""),
        differentiation=data.get("differentiation", ""),
        risk_factors=data.get("risk_factors", []),
        estimated_effort_hours=data.get("estimated_effort_hours", 0.0),
        candidate_count=data.get("candidate_count", 1),
        revision_rounds=data.get("revision_rounds", 1),
        key_criteria=data.get("key_criteria", []),
    )
