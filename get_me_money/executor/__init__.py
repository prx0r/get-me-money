"""Execution lifecycle: acquire capabilities → build → verify → submit → reconcile."""
from __future__ import annotations

import time
from get_me_money.broker import CapabilityBroker, JobPlan
from get_me_money.config import Config
from get_me_money.executor.workers import run_task
from get_me_money.hermes_runtime import HermesError
from get_me_money.models import Attempt, Evaluation, Opportunity, Outcome, Platform
from get_me_money.platforms import BaseAdapter
from get_me_money.verifier import Verifier


class Executor:
    def __init__(self, config: Config, adapters: dict[Platform, BaseAdapter]):
        self.config = config
        self.adapters = adapters
        self.broker = CapabilityBroker(config.work_dir / "jobs", config.hermes.binary)

    async def execute(self, opp: Opportunity, ev: Evaluation) -> Attempt:
        a = Attempt(
            opportunity_id=opp.id, platform=opp.platform, external_id=opp.external_id,
            title=opp.title, metadata={
                "category": opp.category.value,
                "predicted_p": ev.probability_of_success,
                "predicted_cash_ev": ev.ev_cash,
                "estimated_cost": ev.estimated_cost,
                "reward_offered": opp.reward,
            },
        )
        adapter = self.adapters.get(opp.platform)
        if not adapter:
            a.finalize(Outcome.BLOCKED, error="No live adapter")
            return a

        try:
            # Step 1: Claim/check eligibility
            claimed = await adapter.claim(opp)
            if not claimed:
                a.finalize(Outcome.BLOCKED, error="Platform pre-submit/claim gate not satisfied")
                return a

            # Step 2: Build job plan with capability broker
            plan = await self.broker.build_job_profile(opp)
            a.metadata["capabilities_required"] = plan.capabilities.required if plan.capabilities else []
            a.metadata["capabilities_acquiring"] = [ac.name for ac in plan.acquisitions]
            a.metadata["job_workspace"] = plan.workspace

            # Step 3: Execute work via Hermes
            result = await run_task(self.config, opp, ev)
            a.cost = float(result.get("cost", 0) or 0)
            a.metadata["workdir"] = result.get("workdir", "")
            a.metadata["usage"] = result.get("usage", {})
            a.metadata["artifacts"] = result.get("artifacts", [])

            if a.cost > self.config.budget.per_attempt_cap:
                a.finalize(Outcome.FAILED, cost=a.cost, error="Actual Hermes cost exceeded per-attempt cap; result not submitted")
                return a

            # Step 4: Independent verification
            verifier = Verifier(result.get("workdir", ""))
            vresult = await verifier.verify(
                opp,
                result.get("artifacts", []),
                result.get("content", ""),
            )
            a.metadata["verification"] = {
                "score": vresult.score,
                "submittable": vresult.submittable,
                "checks_passed": vresult.checks_passed,
                "checks_failed": vresult.checks_failed,
                "failures": vresult.failures,
                "warnings": vresult.warnings,
            }

            if not vresult.submittable:
                a.finalize(Outcome.FAILED, cost=a.cost,
                           error=f"Verification failed (score={vresult.score:.2f}): {'; '.join(vresult.failures)}")
                return a

            # Step 5: Submit to platform
            submission = await adapter.submit(opp, result)
            if not submission.get("ok"):
                a.finalize(Outcome.FAILED, cost=a.cost, error=submission.get("error", "submission failed"))
                return a

            a.submission_url = str(submission.get("url", result.get("url", "")))
            a.metadata["submission"] = submission
            a.outcome = Outcome.PENDING
            a.updated_at = time.time()
            a.duration_seconds = time.time() - a.started_at

            # Step 6: Record skill performance
            skills_used = (plan.capabilities.already_available +
                          [ac.name for ac in plan.acquisitions])
            a.metadata["skills_used"] = skills_used

            # Step 7: Check immediate status (some platforms settle instantly)
            status = await adapter.check_status(opp)
            self.apply_status(a, status)

        except HermesError as e:
            a.metadata["usage"] = e.usage
            a.finalize(Outcome.FAILED, cost=max(a.cost, e.cost), error=str(e))
        except Exception as e:
            a.finalize(Outcome.FAILED, cost=a.cost, error=f"{type(e).__name__}: {e}")
        return a

    @staticmethod
    def apply_status(a: Attempt, status: dict) -> Attempt:
        if status.get("paid"):
            reward = float(status.get("worker_payment", status.get("reward", 0)) or 0)
            fees = float(status.get("fee", 0) or 0)
            a.finalize(Outcome.SUCCEEDED, reward=reward, fees=fees)
            if status.get("tx_hash"):
                a.metadata["settlement_tx_hash"] = status["tx_hash"]
        elif status.get("terminal") and status.get("won") is False:
            a.finalize(Outcome.REJECTED)
        return a
