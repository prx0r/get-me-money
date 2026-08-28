"""SubmissionRun — the core primitive for learning.

One record per submission attempt. This is the dataset Moltwork
accumulates to learn what process wins what kind of work.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class CandidateRecord:
    version: int = 0
    content: str = ""
    content_hash: str = ""
    artifact_paths: list[str] = field(default_factory=list)
    judge_score: float = 0.0
    gate_passed: bool = False
    submittable: bool = False
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    revision_feedback: str = ""

    def compute_hash(self):
        self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]
        return self.content_hash


@dataclass
class SubmissionRun:
    """One complete submission attempt — from task to outcome to lesson."""

    # IDs (stable references across the chain)
    id: str = field(default_factory=lambda: f"run-{uuid.uuid4().hex[:12]}")
    attempt_id: str = ""  # links to Attempt.id
    workrun_id: str = ""  # links to WorkRun.id

    # Task
    task_title: str = ""
    task_description: str = ""
    task_reward: float = 0.0
    task_platform: str = ""
    task_id: str = ""

    # JobSpec
    jobspec: dict = field(default_factory=dict)

    # Strategy
    strategy_version: str = "default-v1"
    strategy_differentiator: str = ""
    candidate_count: int = 1
    revision_rounds: int = 1

    # Candidates
    candidates: list[CandidateRecord] = field(default_factory=list)

    # Selected
    selected_candidate_version: int = 0

    # External outcome
    external_status: str = ""  # won/lost/pending
    external_score: float = 0.0
    external_rank: int = 0
    external_feedback: str = ""

    # Learning
    postmortem: str = ""
    lessons: list[str] = field(default_factory=list)
    proposed_changes: list[str] = field(default_factory=list)

    # Metadata
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    total_cost: float = 0.0
    model: str = ""
    skills_used: list[str] = field(default_factory=list)

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        (path / "run.json").write_text(json.dumps(asdict(self), indent=2, default=str))

    @classmethod
    def load(cls, path: Path) -> SubmissionRun:
        data = json.loads((path / "run.json").read_text())
        run = cls()
        for k, v in data.items():
            if k == "candidates":
                run.candidates = [CandidateRecord(**c) for c in v]
            elif hasattr(run, k):
                setattr(run, k, v)
        return run

    def best_candidate(self) -> CandidateRecord | None:
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: c.judge_score)

    def summary(self) -> str:
        lines = [
            f"Task: {self.task_title[:60]}",
            f"Reward: ${self.task_reward:.2f}",
            f"Strategy: {self.strategy_version} ({self.strategy_differentiator[:40]})",
            f"Candidates: {len(self.candidates)}",
            f"Selected: v{self.selected_candidate_version}",
            f"External: {self.external_status or 'pending'}",
        ]
        for c in self.candidates:
            lines.append(f"  v{c.version}: score={c.judge_score:.2f} gate={c.gate_passed} hash={c.content_hash}")
        if self.lessons:
            lines.append("Lessons:")
            for l in self.lessons:
                lines.append(f"  - {l}")
        return "\n".join(lines)
