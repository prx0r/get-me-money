"""Memory + Learning — track what works, refine EV estimates over time."""

from __future__ import annotations

import logging
from collections import defaultdict

from get_me_money.ledger import load_attempts, load_strategies, save_strategy
from get_me_money.models import Attempt, Outcome, Strategy

log = logging.getLogger(__name__)


class Memory:
    """Learns from past attempts to improve future evaluations."""

    def __init__(self):
        self.attempts: list[Attempt] = []
        self.strategies: dict[str, Strategy] = {}

    def load(self) -> None:
        self.attempts = load_attempts()
        self.strategies = {}
        for s in load_strategies():
            key = f"{s.category}:{s.platform}"
            self.strategies[key] = s

    def record(self, attempt: Attempt) -> None:
        self.attempts.append(attempt)
        key = f"{attempt.platform.value}:{attempt.category if hasattr(attempt, 'category') else 'unknown'}"

        # Try to get category from opportunity metadata
        cat = attempt.metadata.get("category", "unknown") if hasattr(attempt, 'metadata') else "unknown"
        key = f"{cat}:{attempt.platform.value}"

        if key not in self.strategies:
            self.strategies[key] = Strategy(category=cat, platform=attempt.platform.value)

        s = self.strategies[key]
        s.attempts += 1
        if attempt.outcome == Outcome.SUCCEEDED:
            s.successes += 1
        s.total_reward += attempt.reward
        s.total_cost += attempt.cost + attempt.fees
        s.total_net += attempt.net

        # Recompute averages
        if s.attempts > 0:
            s.win_rate = s.successes / s.attempts
            s.avg_reward = s.total_reward / s.attempts
            s.avg_net = s.total_net / s.attempts
            s.avg_ev_per_attempt = sum(
                a.net for a in self.attempts
                if a.platform.value == s.platform
            ) / max(1, len([
                a for a in self.attempts
                if a.platform.value == s.platform
            ]))

        save_strategy(s)

    def get_strategy(self, category: str, platform: str) -> Strategy | None:
        return self.strategies.get(f"{category}:{platform}")

    def get_win_rate(self, category: str, platform: str) -> float:
        s = self.get_strategy(category, platform)
        return s.win_rate if s else 0.35  # default baseline

    def get_avg_net(self, category: str, platform: str) -> float:
        s = self.get_strategy(category, platform)
        return s.avg_net if s else 0.0

    def best_strategies(self, top_n: int = 5) -> list[Strategy]:
        """Return the most profitable strategies."""
        ranked = sorted(
            self.strategies.values(),
            key=lambda s: s.avg_net,
            reverse=True,
        )
        return [s for s in ranked if s.attempts >= 2][:top_n]

    def worst_strategies(self, bottom_n: int = 3) -> list[Strategy]:
        """Return the least profitable strategies to avoid."""
        ranked = sorted(
            self.strategies.values(),
            key=lambda s: s.avg_net,
        )
        return [s for s in ranked if s.attempts >= 2][:bottom_n]

    def summary(self) -> dict:
        total_attempts = len(self.attempts)
        total_successes = sum(1 for a in self.attempts if a.outcome == Outcome.SUCCEEDED)
        total_reward = sum(a.reward for a in self.attempts)
        total_cost = sum(a.cost + a.fees for a in self.attempts)
        total_net = sum(a.net for a in self.attempts)

        return {
            "total_attempts": total_attempts,
            "total_successes": total_successes,
            "win_rate": total_successes / max(1, total_attempts),
            "total_reward": total_reward,
            "total_cost": total_cost,
            "total_net": total_net,
            "roi_pct": (total_net / max(0.01, total_cost)) * 100,
            "best_strategies": [
                {"cat": s.category, "platform": s.platform,
                 "net": s.avg_net, "win_rate": s.win_rate, "n": s.attempts}
                for s in self.best_strategies()
            ],
            "worst_strategies": [
                {"cat": s.category, "platform": s.platform,
                 "net": s.avg_net, "win_rate": s.win_rate, "n": s.attempts}
                for s in self.worst_strategies()
            ],
        }
