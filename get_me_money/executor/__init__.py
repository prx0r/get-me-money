"""Execution lifecycle: acquire capabilities → build → verify → submit → reconcile."""
from __future__ import annotations

import time
from get_me_money.broker import CapabilityBroker, JobPlan
from get_me_money.config import Config
from get_me_money.executor.workers import run_task
from get_me_money.hermes_runtime import HermesRunner
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

            # Step 3: Execute work via Hermes (with job profile for isolated skills)
            job_profile = {
                "hermes_home": plan.hermes_home,
                "workspace": plan.workspace,
                "skills_installed": plan.skills_installed,
                "acquisitions": [ac.name for ac in plan.acquisitions],
            }
            result = await run_task(self.config, opp, ev, job_profile=job_profile)
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

            # Step 8: Create WorkRun → Moltwork (Product + Receipt + Capability)
            if self.config.platforms.moltwork_enabled:
                self._create_workrun(a, opp, ev, plan, result)

        except HermesError as e:
            a.metadata["usage"] = e.usage
            a.finalize(Outcome.FAILED, cost=max(a.cost, e.cost), error=str(e))
        except Exception as e:
            a.finalize(Outcome.FAILED, cost=a.cost, error=f"{type(e).__name__}: {e}")
        return a

    def _create_workrun(self, a: Attempt, opp: Opportunity, ev: Evaluation,
                        plan: 'JobPlan', result: dict) -> None:
        """Create WorkRun and send to Moltwork."""
        import httpx
        from get_me_money.workrun import WorkRun

        run = WorkRun(
            job_title=opp.title,
            job_description=opp.description[:500],
            job_platform=opp.platform.value,
            job_external_id=opp.external_id,
            job_reward=opp.reward,
            agent_id=self.config.platforms.moltwork_worker_id,
            category=opp.category.value,
            tags=opp.tags + a.metadata.get("skills_used", []),
            artifact_content=result.get("content", ""),
            artifact_files=result.get("artifacts", []),
            verification_score=a.metadata.get("verification", {}).get("score", 0),
            verification_passed=a.metadata.get("verification", {}).get("submittable", False),
            tokens_in=a.metadata.get("usage", {}).get("input_tokens", 0),
            tokens_out=a.metadata.get("usage", {}).get("output_tokens", 0),
            total_cost=a.cost,
            duration_seconds=a.duration_seconds,
            submitted=bool(a.submission_url),
            submission_url=a.submission_url,
            outcome=a.outcome.value,
            reward_earned=a.reward,
            skills_activated=a.metadata.get("skills_used", []),
        )

        try:
            url = self.config.platforms.moltwork_url
            r = httpx.post(f"{url}/api/workruns", json=run.to_dict(), timeout=15)
            r.json()
        except Exception:
            pass  # non-critical, don't fail the attempt

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
