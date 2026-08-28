"""Core data models."""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Platform(str, Enum):
    BOUNTY = "bounty"
    ALGORA = "algora"
    OPIRE = "opire"
    CLUSTLY = "clustly"
    SUPERTEAM = "superteam"
    TASKMARKET = "taskmarket"
    AGENTHANSA = "agenthansa"
    OLAS = "olas"
    VIRTUALS = "virtuals"
    X402 = "x402"
    GIGS = "gigs"
    MOLTJOBS = "moltjobs"
    SPOREAGENT = "sporeagent"
    CUSTOM = "custom"


class TaskCategory(str, Enum):
    RESEARCH = "research"
    CODE_FIX = "code_fix"
    CODE_FEATURE = "code_feature"
    DATA_EXTRACTION = "data_extraction"
    CONTENT = "content"
    DOCUMENTATION = "documentation"
    API_WORK = "api_work"
    TESTING = "testing"
    DESIGN = "design"
    UNKNOWN = "unknown"


class Outcome(str, Enum):
    ATTEMPTED = "attempted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class Opportunity:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    platform: Platform = Platform.CUSTOM
    external_id: str = ""
    title: str = ""
    description: str = ""
    url: str = ""
    reward: float = 0.0
    currency: str = "USD"
    category: TaskCategory = TaskCategory.UNKNOWN
    tags: list[str] = field(default_factory=list)
    posted_at: float = 0.0
    expires_at: float = 0.0
    competition_estimate: int = 0
    verification_strength: float = 0.5  # 0-1, how verifiable is the output
    payment_reliability: float = 0.5    # 0-1, does this platform actually pay
    raw: dict[str, Any] = field(default_factory=dict)
    fetched_at: float = field(default_factory=time.time)

    @property
    def age_hours(self) -> float:
        if not self.posted_at:
            return -1
        return (time.time() - self.posted_at) / 3600

    def fingerprint(self) -> str:
        raw = f"{self.platform.value}:{self.external_id}:{self.title}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class Evaluation:
    opportunity_id: str = ""
    estimated_cost: float = 0.0        # compute + API + fees
    estimated_hours: float = 0.0
    probability_of_success: float = 0.0
    competition_score: float = 0.0     # 0-1, higher = more competition
    ev_cash: float = 0.0
    ev_learning: float = 0.0
    ev_reusable: float = 0.0
    ev_total: float = 0.0
    should_attempt: bool = False
    reasoning: str = ""
    evaluated_at: float = field(default_factory=time.time)

    def compute_ev(self, reward: float, p_success: float, cost: float) -> None:
        self.probability_of_success = p_success
        self.estimated_cost = cost
        self.ev_cash = p_success * reward - cost
        self.ev_total = self.ev_cash + self.ev_learning + self.ev_reusable
        self.should_attempt = self.ev_total > 0 and p_success > 0.15


@dataclass
class Attempt:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    opportunity_id: str = ""
    platform: Platform = Platform.CUSTOM
    external_id: str = ""
    title: str = ""
    outcome: Outcome = Outcome.ATTEMPTED
    reward: float = 0.0
    cost: float = 0.0
    fees: float = 0.0
    net: float = 0.0
    duration_seconds: float = 0.0
    error: str = ""
    submission_url: str = ""
    notes: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def finalize(self, outcome: Outcome, reward: float = 0.0, cost: float = 0.0,
                 fees: float = 0.0, error: str = "") -> None:
        self.outcome = outcome
        self.reward = reward
        self.cost = cost
        self.fees = fees
        self.net = reward - cost - fees
        self.error = error
        self.completed_at = time.time()
        self.duration_seconds = self.completed_at - self.started_at


@dataclass
class PnLSnapshot:
    timestamp: float = field(default_factory=time.time)
    opportunities_seen: int = 0
    opportunities_attempted: int = 0
    successes: int = 0
    failures: int = 0
    skips: int = 0
    gross_earned: float = 0.0
    total_cost: float = 0.0
    total_fees: float = 0.0
    net_earned: float = 0.0
    roi_pct: float = 0.0
    active_work_revenue: float = 0.0
    service_revenue: float = 0.0
    best_platform: str = ""
    best_category: str = ""
    avg_ev_per_attempt: float = 0.0
    strategies: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class Strategy:
    category: str = ""
    platform: str = ""
    attempts: int = 0
    successes: int = 0
    total_reward: float = 0.0
    total_cost: float = 0.0
    total_net: float = 0.0
    avg_ev_per_attempt: float = 0.0
    win_rate: float = 0.0
    avg_reward: float = 0.0
    avg_net: float = 0.0
