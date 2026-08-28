"""Human task queue — local filesystem adapter + Cloudflare Worker bridge.

The agent writes tasks here when it needs human action.
The human sees them on the Cloudflare Worker dashboard and ticks them off.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from get_me_money.config import DATA_DIR


HUMAN_TASKS_FILE = DATA_DIR / "human-tasks.jsonl"


def _load() -> list[dict]:
    if not HUMAN_TASKS_FILE.exists():
        return []
    tasks = []
    for line in HUMAN_TASKS_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                tasks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return tasks


def _save_all(tasks: list[dict]) -> None:
    HUMAN_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HUMAN_TASKS_FILE, "w") as f:
        for t in tasks:
            f.write(json.dumps(t, default=str) + "\n")


def _append(task: dict) -> None:
    HUMAN_TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HUMAN_TASKS_FILE, "a") as f:
        f.write(json.dumps(task, default=str) + "\n")


def create_task(title: str, description: str = "", task_type: str = "action",
                priority: str = "normal", agent_id: str = "",
                metadata: dict[str, Any] | None = None) -> dict:
    """Create a human task. The agent calls this when it needs human action."""
    import random
    task = {
        "id": random.randbytes(4).hex(),
        "title": title,
        "description": description,
        "type": task_type,
        "priority": priority,
        "status": "pending",
        "agent_id": agent_id,
        "created_at": time.time(),
        "completed_at": None,
        "completed_by": None,
        "result": None,
        "metadata": metadata or {},
    }
    _append(task)
    return task


def get_pending() -> list[dict]:
    """Get all pending tasks."""
    return [t for t in _load() if t["status"] == "pending"]


def get_all() -> list[dict]:
    """Get all tasks."""
    return _load()


def complete_task(task_id: str, result: Any = None) -> dict | None:
    """Mark a task as completed by the human."""
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "done"
            t["completed_at"] = time.time()
            t["completed_by"] = "human"
            t["result"] = result
            _save_all(tasks)
            return t
    return None


def reject_task(task_id: str, reason: str = "") -> dict | None:
    """Reject a task."""
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "rejected"
            t["completed_at"] = time.time()
            t["completed_by"] = "human"
            t["result"] = {"reason": reason}
            _save_all(tasks)
            return t
    return None


def check_task(task_id: str) -> dict | None:
    """Check if a task has been completed."""
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None


# Convenience functions for common agent needs

def request_oauth_approval(platform: str, url: str) -> dict:
    """Agent needs human to complete OAuth."""
    return create_task(
        title=f"Connect {platform}",
        description=f"Agent needs you to authorize {platform}.\n\nOpen this URL and click Allow:\n{url}",
        task_type="approval",
        priority="normal",
    )


def request_payout_claim(platform: str, amount: float, details: str = "") -> dict:
    """Agent won money, human needs to claim payout."""
    return create_task(
        title=f"Claim ${amount:.2f} from {platform}",
        description=f"Agent won a bounty on {platform}.\n\n{details}\n\nYou need to complete the payout claim.",
        task_type="action",
        priority="urgent",
        metadata={"amount": amount, "platform": platform},
    )


def request_review(submission_url: str, title: str) -> dict:
    """Agent wants human to review before submitting."""
    return create_task(
        title=f"Review: {title}",
        description=f"Agent wants you to review this submission before it's sent:\n\n{submission_url}",
        task_type="review",
        priority="normal",
    )
