"""WorkerSnapshot — content-addressed immutable configuration.

Every submission references an exact snapshot of the worker's configuration.
Change one prompt → new hash. Change one skill → new hash.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComponentRef:
    """Reference to a versioned component."""
    name: str = ""
    version: str = ""
    digest: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version, "digest": self.digest}


@dataclass
class WorkerSnapshot:
    """Immutable, content-addressed worker configuration."""
    worker_id: str = ""
    worker_name: str = ""
    version: str = "1.0.0"
    runtime: str = "hermes"
    runtime_version: str = ""
    planner_model: str = ""
    builder_model: str = ""
    judge_model: str = ""
    skills: list[ComponentRef] = field(default_factory=list)
    tools: list[ComponentRef] = field(default_factory=list)
    workflow: str = ""
    workflow_version: str = ""
    judge: str = ""
    rubric: str = ""
    threshold: float = 0.6
    max_compute_usd: float = 5.0
    max_wall_minutes: int = 60
    created_at: float = field(default_factory=time.time)
    parent_snapshot: str = ""

    def digest(self) -> str:
        """Content hash — same config → same digest."""
        manifest = {
            "worker_id": self.worker_id, "version": self.version,
            "runtime": self.runtime, "runtime_version": self.runtime_version,
            "planner_model": self.planner_model, "builder_model": self.builder_model,
            "judge_model": self.judge_model,
            "skills": [s.to_dict() for s in self.skills],
            "tools": [t.to_dict() for t in self.tools],
            "workflow": self.workflow, "workflow_version": self.workflow_version,
            "judge": self.judge, "rubric": self.rubric, "threshold": self.threshold,
        }
        return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id, "worker_name": self.worker_name,
            "version": self.version, "runtime": self.runtime,
            "digest": self.digest(),
            "skills": [s.to_dict() for s in self.skills],
            "tools": [t.to_dict() for t in self.tools],
            "workflow": self.workflow, "threshold": self.threshold,
            "parent_snapshot": self.parent_snapshot, "created_at": self.created_at,
        }

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        (path / "snapshot.json").write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> WorkerSnapshot:
        data = json.loads((path / "snapshot.json").read_text())
        snap = cls()
        for k, v in data.items():
            if k == "skills": snap.skills = [ComponentRef(**s) for s in v]
            elif k == "tools": snap.tools = [ComponentRef(**t) for t in v]
            elif hasattr(snap, k): setattr(snap, k, v)
        return snap
