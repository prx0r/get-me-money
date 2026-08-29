"""RunMeter — tracks exact spending during execution."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CostEvent:
    timestamp: float = 0.0
    event_type: str = ""
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class RunMeter:
    def __init__(self):
        self.events: list[CostEvent] = []
        self.total_cost: float = 0.0

    def record(self, event: CostEvent):
        self.events.append(event)
        self.total_cost += event.cost_usd

    def record_llm(self, model: str, input_tokens: int, output_tokens: int, cost: float):
        self.record(CostEvent(event_type="llm", model=model,
                              input_tokens=input_tokens, output_tokens=output_tokens,
                              cost_usd=cost, timestamp=time.time()))

    def record_api(self, provider: str, resource: str, cost: float):
        self.record(CostEvent(event_type="api", provider=provider, resource=resource,
                              cost_usd=cost, timestamp=time.time()))

    def record_purchase(self, item: str, cost: float):
        self.record(CostEvent(event_type="purchase", resource=item,
                              cost_usd=cost, timestamp=time.time()))
