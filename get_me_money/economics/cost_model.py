"""CostModel — historical benchmark prior.

Records task_type × model → cost distribution.
Estimates low/expected/high/hard_cap from history.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CostEnvelope:
    low: float = 0.0
    expected: float = 0.0
    high: float = 0.0
    hard_cap: float = 0.0


class CostModel:
    def __init__(self):
        self._history: dict[str, list[dict]] = {}

    def record(self, task_type: str, model: str, cost: float, success: bool):
        key = f"{task_type}:{model}"
        if key not in self._history:
            self._history[key] = []
        self._history[key].append({"cost": cost, "success": success, "timestamp": time.time()})

    def estimate(self, task_type: str, model: str = "") -> CostEnvelope:
        key = f"{task_type}:{model}"
        runs = self._history.get(key, [])
        if not runs:
            return CostEnvelope(low=0.05, expected=0.20, high=0.50, hard_cap=1.0)
        costs = sorted([r["cost"] for r in runs])
        n = len(costs)
        return CostEnvelope(
            low=costs[0],
            expected=costs[n // 2],
            high=costs[min(int(n * 0.9), n - 1)],
            hard_cap=costs[min(int(n * 0.9), n - 1)] * 1.5,
        )

    def success_rate(self, task_type: str, model: str = "") -> float:
        runs = self._history.get(f"{task_type}:{model}", [])
        if not runs:
            return 0.5
        return sum(1 for r in runs if r["success"]) / len(runs)

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        (path / "cost_model.json").write_text(json.dumps(self._history, indent=2))

    def load(self, path: Path):
        p = path / "cost_model.json"
        if p.exists():
            self._history = json.loads(p.read_text())
