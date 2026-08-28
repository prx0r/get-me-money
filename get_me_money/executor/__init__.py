"""Executor + Verifier — attempt work and validate results."""

from __future__ import annotations

import logging
import time
from typing import Optional

from get_me_money.config import Config
from get_me_money.identity import IdentityManager
from get_me_money.models import (
    Attempt, Evaluation, Opportunity, Outcome, Platform,
)
from get_me_money.platforms import BaseAdapter

log = logging.getLogger(__name__)


class Executor:
    """Manages the attempt lifecycle: claim → execute → submit → verify."""

    def __init__(self, config: Config, adapters: dict[Platform, BaseAdapter],
                 identity: IdentityManager | None = None):
        self.config = config
        self.adapters = adapters
        self.identity = identity or IdentityManager()

    async def execute(self, opp: Opportunity, ev: Evaluation) -> Attempt:
        """Full execution pipeline for a single opportunity."""
        attempt = Attempt(
            opportunity_id=opp.id,
            platform=opp.platform,
            external_id=opp.external_id,
            title=opp.title,
            started_at=time.time(),
        )

        # Pre-flight: check auth
        needs_human, reason = self.identity.needs_human_action(opp.platform.value)
        if needs_human:
            log.warning("Skipping %s — needs human auth: %s", opp.title, reason)
            attempt.notes = f"Skipped: needs human auth — {reason}"
            attempt.finalize(Outcome.SKIPPED, error=reason)
            return attempt

        adapter = self.adapters.get(opp.platform)
        if not adapter:
            attempt.finalize(Outcome.FAILED, cost=0, error=f"No adapter for {opp.platform}")
            return attempt

        try:
            # Step 1: Claim
            log.info("Claiming: %s on %s", opp.title, opp.platform.value)
            claimed = await adapter.claim(opp)
            if not claimed:
                attempt.finalize(Outcome.REJECTED, error="Could not claim")
                return attempt

            # Step 2: Execute the actual work
            log.info("Executing: %s", opp.title)
            result = await self._do_work(opp, ev)
            if not result.get("success"):
                attempt.finalize(
                    Outcome.FAILED,
                    error=result.get("error", "Work execution failed"),
                )
                return attempt

            # Step 3: Submit
            log.info("Submitting: %s", opp.title)
            submitted = await adapter.submit(opp, result)
            if not submitted:
                attempt.finalize(Outcome.FAILED, error="Submission failed")
                return attempt

            # Step 4: Verify (check if accepted/paid)
            log.info("Verifying: %s", opp.title)
            status = await adapter.check_status(opp)
            paid = status.get("paid", False) or status.get("status") == "completed"

            if paid:
                attempt.finalize(
                    Outcome.SUCCEEDED,
                    reward=opp.reward,
                    cost=ev.estimated_cost,
                    fees=opp.reward * 0.1,  # estimate fees
                )
            else:
                # Submitted but not yet verified — mark as attempted
                attempt.outcome = Outcome.ATTEMPTED
                attempt.submission_url = result.get("url", "")
                attempt.completed_at = time.time()
                attempt.duration_seconds = attempt.completed_at - attempt.started_at
                attempt.cost = ev.estimated_cost

        except Exception as e:
            log.error("Execution error for %s: %s", opp.title, e)
            attempt.finalize(Outcome.FAILED, error=str(e))

        return attempt

    async def _do_work(self, opp: Opportunity, ev: Evaluation) -> dict:
        """Dispatch to the appropriate worker based on category.

        This is the core "do real work" function. Each category has a
        specialized handler.
        """
        from get_me_money.executor.workers import (
            run_research_task,
            run_code_fix_task,
            run_data_extraction_task,
            run_content_task,
        )

        handlers = {
            "research": run_research_task,
            "code_fix": run_code_fix_task,
            "code_feature": run_code_fix_task,
            "data_extraction": run_data_extraction_task,
            "content": run_content_task,
            "documentation": run_content_task,
            "api_work": run_data_extraction_task,
            "testing": run_code_fix_task,
        }

        handler = handlers.get(opp.category.value, run_research_task)
        return await handler(opp, ev)
