"""Reforecaster — updates estimates mid-run."""
from __future__ import annotations

from dataclasses import dataclass
from get_me_money.economics.cost_model import CostModel, CostEnvelope
from get_me_money.economics.run_meter import RunMeter


@dataclass
class RunEconomics:
    reward_usd: float = 0.0
    spent_usd: float = 0.0
    projected_low: float = 0.0
    projected_expected: float = 0.0
    projected_high: float = 0.0
    p_success: float = 0.0
    expected_payout: float = 0.0
    expected_net: float = 0.0
    decision: str = "continue"

from dataclasses import dataclass


class Reforecaster:
    def __init__(self, cost_model: CostModel, meter: RunMeter):
        self.cost_model = cost_model
        self.meter = meter

    def reforecast(self, task_type: str, model: str, reward: float,
                   progress: float = 0.0) -> RunEconomics:
        envelope = self.cost_model.estimate(task_type, model)
        p_success = self.cost_model.success_rate(task_type, model)
        spent = self.meter.total_cost
        remaining = envelope.expected * (1 - progress)
        expected_total = spent + remaining
        expected_payout = p_success * reward
        expected_net = expected_payout - expected_total

        return RunEconomics(
            reward_usd=reward, spent_usd=spent,
            projected_low=envelope.low * (1 - progress),
            projected_expected=remaining,
            projected_high=envelope.high * (1 - progress),
            p_success=p_success,
            expected_payout=expected_payout,
            expected_net=expected_net,
            decision="continue" if expected_net > 0 else "abort",
        )
