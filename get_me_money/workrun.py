"""WorkRun — the immutable trace of one job execution.

Every time an agent undertakes a task, create one WorkRun.
This is the raw material that becomes Product + Receipt + Skill.

Flow:
  WorkRun (private trace)
      ↓
  sanitize
      ↓
  ┌───┼───┐
  ▼   ▼   ▼
  Product  Receipt  SkillCandidate
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkRun:
    """Immutable trace of one job execution."""
    id: str = field(default_factory=lambda: f"run-{uuid.uuid4().hex[:12]}")

    # Brief
    job_title: str = ""
    job_description: str = ""
    job_platform: str = ""
    job_external_id: str = ""
    job_reward: float = 0.0

    # Agent
    agent_id: str = ""
    runtime: str = "hermes"
    model: str = ""

    # Inputs
    input_files: list[str] = field(default_factory=list)
    input_urls: list[str] = field(default_factory=list)
    input_prompt: str = ""

    # Process
    steps: list[dict] = field(default_factory=list)
    # each step: {name, tool, input_summary, output_summary, duration_ms, tokens}
    decisions: list[str] = field(default_factory=list)
    sources_accessed: list[str] = field(default_factory=list)

    # Artifacts
    artifact_files: list[str] = field(default_factory=list)
    artifact_content: str = ""  # the actual output text
    artifact_schema: dict = field(default_factory=dict)

    # Verification
    verification_score: float = 0.0
    verification_passed: bool = False
    verification_checks: list[dict] = field(default_factory=list)

    # Cost
    tokens_in: int = 0
    tokens_out: int = 0
    api_cost: float = 0.0
    total_cost: float = 0.0
    duration_seconds: float = 0.0

    # Outcome
    submitted: bool = False
    submission_url: str = ""
    outcome: str = ""  # succeeded, failed, rejected, pending
    reward_earned: float = 0.0

    # Skills observed
    skills_activated: list[str] = field(default_factory=list)
    skill_candidate: dict = field(default_factory=dict)
    # {name, description, eval_pass_rate, procedure_summary}

    # Metadata
    tags: list[str] = field(default_factory=list)
    category: str = "general"
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    def content_hash(self) -> str:
        """Deterministic hash of the run for content addressing."""
        raw = f"{self.job_title}:{self.agent_id}:{self.created_at}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "job_title": self.job_title,
            "job_platform": self.job_platform,
            "job_external_id": self.job_external_id,
            "job_reward": self.job_reward,
            "agent_id": self.agent_id,
            "runtime": self.runtime,
            "category": self.category,
            "steps_count": len(self.steps),
            "artifacts_count": len(self.artifact_files),
            "verification_score": self.verification_score,
            "verification_passed": self.verification_passed,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "total_cost": self.total_cost,
            "duration_seconds": self.duration_seconds,
            "outcome": self.outcome,
            "reward_earned": self.reward_earned,
            "skills_activated": self.skills_activated,
            "has_skill_candidate": bool(self.skill_candidate),
            "tags": self.tags,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "content_hash": self.content_hash(),
        }
        return d

    def to_private_trace(self) -> dict:
        """Full trace — never published, only used for skill synthesis."""
        return {
            **self.to_dict(),
            "job_description": self.job_description,
            "input_files": self.input_files,
            "input_urls": self.input_urls,
            "input_prompt": self.input_prompt,
            "steps": self.steps,
            "decisions": self.decisions,
            "sources_accessed": self.sources_accessed,
            "artifact_files": self.artifact_files,
            "artifact_content": self.artifact_content,
            "artifact_schema": self.artifact_schema,
            "verification_checks": self.verification_checks,
            "skill_candidate": self.skill_candidate,
            "submission_url": self.submission_url,
        }

    def to_product_args(self) -> dict:
        """Convert to Moltwork /api/import arguments."""
        # Sanitize: remove private data, generalize
        text = self.artifact_content
        if not text or len(text) < 100:
            text = f"# {self.job_title}\n\nCompleted {self.category} work. {len(self.artifact_files)} artifacts produced."

        return {
            "title": self.job_title,
            "text": text,
            "worker_id": self.agent_id,
            "source": self.job_platform,
            "source_job_id": self.job_external_id,
            "category": self.category,
            "tags": self.tags,
            "price": 0.0,  # auto-suggest
            "license": "reuse permitted",
        }

    def to_receipt_args(self) -> dict:
        """Convert to Moltwork /api/receipts arguments."""
        return {
            "agent_id": self.agent_id,
            "job_source": self.job_platform,
            "job_id": self.job_external_id,
            "capability": self.category,
            "input_hash": hashlib.sha256(self.job_title.encode()).hexdigest()[:16],
            "output_hash": self.content_hash(),
            "output_preview": self.job_title[:200],
            "status": self.outcome,
            "amount_earned": self.reward_earned,
            "currency": "USDC",
        }

    def to_capability_args(self) -> dict:
        """Convert to Moltwork /api/capabilities arguments."""
        desc = f"Completed {self.category} work: {self.job_title}"
        if self.verification_passed:
            desc += " (verified)"
        return {
            "agent_id": self.agent_id,
            "name": self.category,
            "description": desc,
        }
