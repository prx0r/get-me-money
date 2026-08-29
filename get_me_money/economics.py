"""Economics — cost model, run meter, reforecaster.

Every worker knows the economics of its own execution while working.
Not "can I complete this?" but "is completing this still worth the money?"

Architecture:
  COST MODEL    historical benchmark prior
  PREFLIGHT     route + projected envelope
  RUN METER     exact spending during execution
  REFORECASTER  update estimates mid-run
  OUTCOME       actual cost-to-success → updates cost model
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CostEvent:
    """One economic event during execution."""
    timestamp: float = 0.0
    event_type: str = ""  # llm, api, x402, compute, chain, purchased_asset, purchased_service
    provider: str = ""
    resource: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cache_tokens: int = 0
    quantity: int = 1
    cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp, "type": self.event_type,
            "provider": self.provider, "model": self.model,
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
        }


@dataclass
class CostEnvelope:
    """Three budget values — not one fake number."""
    low: float = 0.0       # best case
    expected: float = 0.0  # median from history
    high: float = 0.0      # p90 from history
    hard_cap: float = 0.0  # maximum authorized


@dataclass
class RunEconomics:
    """Live economics during a run."""
    reward_usd: float = 0.0
    spent_usd: float = 0.0
    projected_remaining: CostEnvelope = field(default_factory=CostEnvelope)
    p_success: float = 0.0
    expected_payout: float = 0.0
    expected_incremental_ev: float = 0.0
    decision: str = ""  # continue, reroute, abort

    def to_dict(self) -> dict:
        return {
            "reward_usd": self.reward_usd,
            "spent_usd": self.spent_usd,
            "p_success": self.p_success,
            "expected_payout": self.expected_payout,
            "expected_incremental_ev": self.expected_incremental_ev,
            "decision": self.decision,
        }


class CostModel:
    """Historical benchmark — what does it cost to do this kind of work?"""

    def __init__(self):
        self._history: dict[str, list[dict]] = {}  # task_key → list of run records

    def record(self, task_type: str, model: str, cost: float, success: bool):
        """Record a completed run."""
        key = f"{task_type}:{model}"
        if key not in self._history:
            self._history[key] = []
        self._history[key].append({
            "cost": cost, "success": success, "timestamp": time.time(),
        })

    def estimate(self, task_type: str, model: str = "") -> CostEnvelope:
        """Estimate cost from historical runs."""
        key = f"{task_type}:{model}"
        runs = self._history.get(key, [])

        if not runs:
            # No history — use defaults
            return CostEnvelope(low=0.05, expected=0.20, high=0.50, hard_cap=1.0)

        costs = sorted([r["cost"] for r in runs])
        n = len(costs)

        low = costs[0] if n > 0 else 0.05
        expected = costs[n // 2] if n > 0 else 0.20  # median
        p90_idx = min(int(n * 0.9), n - 1)
        high = costs[p90_idx] if n > 0 else 0.50

        return CostEnvelope(
            low=low,
            expected=expected,
            high=high,
            hard_cap=high * 1.5,  # 150% of p90
        )

    def success_rate(self, task_type: str, model: str = "") -> float:
        key = f"{task_type}:{model}"
        runs = self._history.get(key, [])
        if not runs:
            return 0.5  # prior
        successes = sum(1 for r in runs if r["success"])
        return successes / len(runs)

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        (path / "cost_model.json").write_text(json.dumps(self._history, indent=2))

    def load(self, path: Path):
        p = path / "cost_model.json"
        if p.exists():
            self._history = json.loads(p.read_text())


class RunMeter:
    """Tracks exact spending during a run."""

    def __init__(self):
        self.events: list[CostEvent] = []
        self.total_cost: float = 0.0

    def record(self, event: CostEvent):
        self.events.append(event)
        self.total_cost += event.cost_usd

    def record_llm(self, model: str, input_tokens: int, output_tokens: int, cost: float):
        self.record(CostEvent(
            event_type="llm", model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            cost_usd=cost, timestamp=time.time(),
        ))

    def record_api(self, provider: str, resource: str, cost: float):
        self.record(CostEvent(
            event_type="api", provider=provider, resource=resource,
            cost_usd=cost, timestamp=time.time(),
        ))

    def record_purchase(self, item: str, cost: float):
        self.record(CostEvent(
            event_type="purchased_asset", resource=item,
            cost_usd=cost, timestamp=time.time(),
        ))

    def snapshot(self) -> dict:
        return {
            "spent_usd": self.total_cost,
            "events": len(self.events),
            "llm_events": sum(1 for e in self.events if e.event_type == "llm"),
            "api_events": sum(1 for e in self.events if e.event_type == "api"),
        }


class Reforecaster:
    """Updates economic projections mid-run."""

    def __init__(self, cost_model: CostModel, meter: RunMeter):
        self.cost_model = cost_model
        self.meter = meter

    def reforecast(self, task_type: str, model: str, reward: float,
                   progress: float = 0.0) -> RunEconomics:
        """Recalculate economics based on actual spending so far."""
        envelope = self.cost_model.estimate(task_type, model)
        p_success = self.cost_model.success_rate(task_type, model)

        spent = self.meter.total_cost
        remaining_expected = envelope.expected * (1 - progress)

        expected_total = spent + remaining_expected
        expected_payout = p_success * reward
        expected_net = expected_payout - expected_total

        return RunEconomics(
            reward_usd=reward,
            spent_usd=spent,
            projected_remaining=CostEnvelope(
                low=envelope.low * (1 - progress),
                expected=remaining_expected,
                high=envelope.high * (1 - progress),
                hard_cap=envelope.hard_cap,
            ),
            p_success=p_success,
            expected_payout=expected_payout,
            expected_incremental_ev=expected_net,
            decision="continue" if expected_net > 0 else "abort",
        )
