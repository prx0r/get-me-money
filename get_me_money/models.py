"""Core production data models for get-me-money."""
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
    MOLTJOBS = "moltjobs"
    AGENTHANSA = "agenthansa"
    OLAS = "olas"
    VIRTUALS = "virtuals"
    X402 = "x402"
    GIGS = "gigs"
    APIFY = "apify"
    ETSY = "etsy"
    ROBLOX = "roblox"
    GUMROAD = "gumroad"
    APPLE = "apple"
    GOOGLE_PLAY = "google_play"
    ITCHIO = "itchio"
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
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    PAUSED_HUMAN = "paused_human"


# ─── Opportunity: the universal top-level object ─────────────────────

class OpportunityType(str, Enum):
    """What kind of economic output does this produce?"""
    DATA = "data"              # extraction, processing, monitoring
    CODE = "code"              # bugs, features, integrations, tests
    RESEARCH = "research"      # analysis, reports, intelligence
    CONTENT = "content"        # writing, docs, templates
    TOOL = "tool"              # Actor, API, MCP, app, plugin
    ASSET = "asset"            # 3D model, design, template
    SERVICE = "service"        # endpoint, worker, SaaS


class ExecutionMode(int, Enum):
    """How does it get to market?"""
    AUTONOMOUS = 0       # agent does everything
    HUMAN_GATED = 1      # agent produces, human handles 1-2 specific gates


class RewardModel(str, Enum):
    """How does value flow?"""
    FIXED = "fixed"             # bounty: fixed payment on completion
    PRIZE = "prize"             # competition: probabilistic, winner-take-all
    REPEAT_SALES = "repeat_sales"  # product: ongoing sales
    USAGE = "usage"             # service: per-call revenue
    SUBSCRIPTION = "subscription"  # recurring revenue
    EXPLORATORY = "exploratory"  # no guaranteed revenue (research, portfolio)


@dataclass
class HumanGate:
    """A point where human action is required before the agent can continue."""
    stage: str = ""       # "registration", "submission", "payment", "legal", "approval"
    reason: str = ""      # why human is needed
    estimated_time: str = ""  # "5 minutes", "1 hour", "1 day"


@dataclass
class Opportunity:
    """Universal top-level economic opportunity.

    NOT all opportunities are jobs. A Roblox template, an x402 endpoint,
    a $20 bounty, and a hackathon are all economically different but share
    a common shape: demand → artifact → value → constraints → human involvement.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # What kind of opportunity
    opportunity_type: OpportunityType = OpportunityType.DATA
    category: TaskCategory = TaskCategory.UNKNOWN

    # How can it be executed?
    execution_mode: ExecutionMode = ExecutionMode.AUTONOMOUS
    human_gates: list[HumanGate] = field(default_factory=list)

    # What's the reward structure?
    reward_model: RewardModel = RewardModel.FIXED
    reward: float = 0.0
    currency: str = "USD"
    max_reward: float = 0.0  # for probabilistic prizes
    recent_units_sold: int = 0  # for repeat_sales

    # Core identity
    platform: Platform = Platform.CUSTOM
    external_id: str = ""
    title: str = ""
    description: str = ""
    url: str = ""
    tags: list[str] = field(default_factory=list)

    # Timing
    posted_at: float = 0.0
    expires_at: float = 0.0
    deadline: str = ""

    # Competition/intelligence
    competition_estimate: int = 0
    verification_strength: float = 0.5
    payment_reliability: float = 0.5

    # Raw data from source
    raw: dict[str, Any] = field(default_factory=dict)
    fetched_at: float = field(default_factory=time.time)

    @property
    def age_hours(self) -> float:
        if not self.posted_at:
            return -1
        return (time.time() - self.posted_at) / 3600

    @property
    def is_autonomous(self) -> bool:
        return self.execution_mode == ExecutionMode.AUTONOMOUS

    @property
    def has_human_gates(self) -> bool:
        return len(self.human_gates) > 0

    def fingerprint(self) -> str:
        stable = self.external_id or self.url or self.title
        raw = f"{self.platform.value}:{stable}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "opportunity_type": self.opportunity_type.value,
            "category": self.category.value,
            "execution_mode": self.execution_mode.value,
            "human_gates": [{"stage": g.stage, "reason": g.reason} for g in self.human_gates],
            "reward_model": self.reward_model.value,
            "reward": self.reward,
            "currency": self.currency,
            "max_reward": self.max_reward,
            "platform": self.platform.value,
            "external_id": self.external_id,
            "title": self.title,
            "description": self.description[:200],
            "tags": self.tags,
            "competition_estimate": self.competition_estimate,
        }


# ─── Evaluation ──────────────────────────────────────────────────────

@dataclass
class Evaluation:
    opportunity_id: str = ""
    estimated_cost: float = 0.0
    estimated_hours: float = 0.0
    probability_of_success: float = 0.0
    competition_score: float = 0.0
    platform_fee_rate: float = 0.0
    ev_cash: float = 0.0
    learning_score: float = 0.0
    reusable_score: float = 0.0
    rank_score: float = 0.0
    should_attempt: bool = False
    reasoning: str = ""
    evaluated_at: float = field(default_factory=time.time)


# ─── Attempt ─────────────────────────────────────────────────────────

@dataclass
class Attempt:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    opportunity_id: str = ""
    platform: Platform = Platform.CUSTOM
    external_id: str = ""
    title: str = ""
    outcome: Outcome = Outcome.PENDING
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
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def finalize(self, outcome: Outcome, reward: float | None = None,
                 cost: float | None = None, fees: float | None = None,
                 error: str = "") -> None:
        self.outcome = outcome
        if reward is not None:
            self.reward = reward
        if cost is not None:
            self.cost = cost
        if fees is not None:
            self.fees = fees
        self.net = self.reward - self.cost - self.fees
        self.error = error
        now = time.time()
        self.updated_at = now
        if outcome != Outcome.PENDING:
            self.completed_at = now
        self.duration_seconds = now - self.started_at


# ─── Strategy / PnL ─────────────────────────────────────────────────

@dataclass
class Strategy:
    category: str = ""
    platform: str = ""
    attempts: int = 0
    successes: int = 0
    total_reward: float = 0.0
    total_cost: float = 0.0
    total_net: float = 0.0
    win_rate: float = 0.0
    avg_reward: float = 0.0
    avg_net: float = 0.0


@dataclass
class PnLSnapshot:
    timestamp: float = field(default_factory=time.time)
    opportunities_seen: int = 0
    opportunities_attempted: int = 0
    pending: int = 0
    successes: int = 0
    failures: int = 0
    skips: int = 0
    gross_earned: float = 0.0
    total_cost: float = 0.0
    total_fees: float = 0.0
    net_earned: float = 0.0
    roi_pct: float = 0.0
    best_platform: str = ""
    best_category: str = ""
    strategies: dict[str, dict[str, float]] = field(default_factory=dict)
