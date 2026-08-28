"""All task categories use the real Hermes runtime; no synthetic success paths."""
from __future__ import annotations
from get_me_money.config import Config
from get_me_money.hermes_runtime import HermesRunner
from get_me_money.models import Evaluation, Opportunity


async def run_task(config: Config, opp: Opportunity, ev: Evaluation) -> dict:
    return await HermesRunner(config).run(opp, ev)
