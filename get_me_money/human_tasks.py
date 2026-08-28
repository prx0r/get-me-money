"""Human task queue — first-class subsystem for human-agent collaboration.

Agent autonomous by default; human only handles irreversible, identity-bound,
legal, high-risk, or ambiguous actions.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from get_me_money.config import DATA_DIR


HUMAN_TASKS_FILE = DATA_DIR / "human-tasks.jsonl"

# Task types
AUTH = "auth"              # OAuth / API key / account connection
IDENTITY = "identity"      # KYC / age / identity verification
LEGAL = "legal"            # Terms acceptance / contract / policy change
APPROVAL = "approval"      # Agent wants permission for significant action
PAYMENT = "payment"        # Funding / payout / withdrawal
SECRET = "secret"          # API credential required
AMBIGUITY = "ambiguity"    # Agent genuinely cannot infer user intent
SECURITY = "security"      # Suspicious skill/tool/site needs review
EXCEPTION = "exception"    # Agent got stuck after automated recovery

TASK_TYPES = {AUTH, IDENTITY, LEGAL, APPROVAL, PAYMENT, SECRET, AMBIGUITY, SECURITY, EXCEPTION}

# Priority levels
URGENT = "urgent"
HIGH = "high"
NORMAL = "normal"
LOW = "low"


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


def _ev_priority(estimated_value: float, urgency: str, effort_seconds: float) -> float:
    """Compute EV-based priority score. Higher = more important."""
    urgency_mult = {"urgent": 4.0, "high": 2.0, "normal": 1.0, "low": 0.5}.get(urgency, 1.0)
    effort_minutes = max(0.5, effort_seconds / 60.0)
    return (estimated_value * urgency_mult) / effort_minutes


def create_task(title: str, description: str = "", task_type: str = APPROVAL,
                priority: str = NORMAL, agent_id: str = "",
                estimated_value: float = 0.0, effort_seconds: float = 60,
                deadline: str = "", job_id: str = "",
                agent_progress: list[str] | None = None,
                requested_action: str = "", resume_event: str = "",
                metadata: dict[str, Any] | None = None) -> dict:
    """Create a human task with full metadata."""
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
        "estimated_value": estimated_value,
        "effort_seconds": effort_seconds,
        "ev_priority": _ev_priority(estimated_value, priority, effort_seconds),
        "deadline": deadline,
        "job_id": job_id,
        "agent_progress": agent_progress or [],
        "requested_action": requested_action,
        "resume_event": resume_event,
        "metadata": metadata or {},
    }
    _append(task)
    return task


def get_pending() -> list[dict]:
    """Get pending tasks sorted by EV priority (highest first)."""
    tasks = [t for t in _load() if t["status"] == "pending"]
    return sorted(tasks, key=lambda t: t.get("ev_priority", 0), reverse=True)


def get_all() -> list[dict]:
    return _load()


def complete_task(task_id: str, result: Any = None) -> dict | None:
    """Mark task as completed by human."""
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
    tasks = _load()
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None


def batch_summary() -> dict:
    """Summarize pending tasks for batch notification."""
    pending = get_pending()
    if not pending:
        return {"count": 0, "total_ev": 0, "tasks": []}

    total_ev = sum(t.get("estimated_value", 0) for t in pending)
    return {
        "count": len(pending),
        "total_ev": round(total_ev, 2),
        "tasks": [
            {
                "id": t["id"],
                "title": t["title"],
                "type": t["type"],
                "priority": t["priority"],
                "ev": t.get("estimated_value", 0),
                "reason": t.get("description", ""),
            }
            for t in pending[:10]
        ],
    }


# === Convenience creators for common scenarios ===

def request_oauth(platform: str, url: str, job_id: str = "",
                  estimated_value: float = 0.0) -> dict:
    """Agent needs human to complete OAuth."""
    return create_task(
        title=f"Connect {platform}",
        description=f"Agent needs you to authorize {platform}.\n\nOpen this URL and click Allow:\n{url}",
        task_type=AUTH,
        priority=HIGH if estimated_value > 50 else NORMAL,
        estimated_value=estimated_value,
        effort_seconds=30,
        job_id=job_id,
        agent_progress=["found opportunity", "estimated EV", "needs access"],
        requested_action=f"oauth_{platform}",
        resume_event=f"{platform}_connected",
    )


def request_payout(platform: str, amount: float, details: str = "",
                   job_id: str = "") -> dict:
    """Agent won money, human needs to claim payout."""
    return create_task(
        title=f"Claim ${amount:.2f} from {platform}",
        description=f"Agent won a bounty on {platform}.\n\n{details}\n\nYou need to complete the payout claim.",
        task_type=PAYMENT,
        priority=URGENT,
        estimated_value=amount,
        effort_seconds=120,
        job_id=job_id,
        agent_progress=["work submitted", "work accepted", "prize confirmed"],
        requested_action=f"claim_{platform}",
        resume_event=f"{platform}_claimed",
        metadata={"amount": amount, "platform": platform},
    )


def request_approval(title: str, description: str, cost: float,
                     expected_value: float, job_id: str = "") -> dict:
    """Agent wants permission for a spending action."""
    return create_task(
        title=title,
        description=description,
        task_type=APPROVAL,
        priority=NORMAL,
        estimated_value=expected_value,
        effort_seconds=10,
        job_id=job_id,
        agent_progress=["analyzed opportunity", "computed EV"],
        requested_action="approve_spend",
        resume_event="spend_approved",
        metadata={"cost": cost, "expected_value": expected_value},
    )


def request_credential(service: str, purpose: str, job_id: str = "",
                       estimated_value: float = 0.0) -> dict:
    """Agent needs an API key or credential."""
    return create_task(
        title=f"Add {service} API key",
        description=f"Agent needs {service} credentials for: {purpose}",
        task_type=SECRET,
        priority=NORMAL,
        estimated_value=estimated_value,
        effort_seconds=60,
        job_id=job_id,
        requested_action=f"credential_{service}",
        resume_event=f"{service}_configured",
    )


def request_security_review(title: str, description: str,
                            job_id: str = "") -> dict:
    """Agent found something suspicious that needs human review."""
    return create_task(
        title=title,
        description=description,
        task_type=SECURITY,
        priority=HIGH,
        effort_seconds=30,
        job_id=job_id,
        requested_action="security_review",
    )


def report_exception(title: str, description: str,
                     job_id: str = "") -> dict:
    """Agent got stuck and needs human help."""
    return create_task(
        title=title,
        description=description,
        task_type=EXCEPTION,
        priority=HIGH,
        effort_seconds=120,
        job_id=job_id,
        requested_action="resolve_exception",
    )
