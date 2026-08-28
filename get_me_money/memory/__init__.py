"""Outcome memory used to calibrate future probability estimates."""
from __future__ import annotations
from collections import defaultdict
from get_me_money.ledger import load_attempts
from get_me_money.models import Outcome, Strategy


class Memory:
    def __init__(self) -> None:
        self.attempts = load_attempts()

    def strategy(self, category: str, platform: str) -> Strategy:
        rows = [a for a in self.attempts if a.platform.value == platform and a.metadata.get("category") == category and a.outcome != Outcome.PENDING]
        s = Strategy(category=category, platform=platform, attempts=len(rows))
        s.successes = sum(a.outcome == Outcome.SUCCEEDED for a in rows)
        s.total_reward = sum(a.reward for a in rows)
        s.total_cost = sum(a.cost + a.fees for a in rows)
        s.total_net = sum(a.net for a in rows)
        if rows:
            s.win_rate = s.successes / len(rows)
            s.avg_reward = s.total_reward / len(rows)
            s.avg_net = s.total_net / len(rows)
        return s

    def calibrated_probability(self, category: str, platform: str, prior: float) -> float:
        """Beta-binomial shrinkage so a few lucky wins do not dominate."""
        s = self.strategy(category, platform)
        prior_strength = 6.0
        alpha = prior * prior_strength + s.successes
        beta = (1.0 - prior) * prior_strength + (s.attempts - s.successes)
        return alpha / max(1e-9, alpha + beta)
