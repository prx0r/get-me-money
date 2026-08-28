"""Execution lifecycle: JobSpec → WinPlan → Build → Judge → Submit → Learn."""
from __future__ import annotations

import time
from get_me_money.broker import CapabilityBroker, JobPlan
from get_me_money.config import Config
from get_me_money.executor.workers import run_task
from get_me_money.hermes_runtime import HermesRunner
from get_me_money.hermes_runtime import HermesError
from get_me_money.jobspec import JobSpec, WinPlan
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
            a.metadata["job_workspace"] = plan.workspace

            # Step 3: Build job profile for hermes
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

            # Step 4: Independent verification (deterministic gate + judge)
            verifier = Verifier(result.get("workdir", ""), jobspec=result.get("jobspec"))
            vresult = await verifier.verify(
                opp,
                result.get("artifacts", []),
                result.get("content", ""),
                jobspec=result.get("jobspec"),
            )
            a.metadata["verification"] = {
                "gate_passed": vresult.gate_passed,
                "gate_score": vresult.gate_score,
                "gate_checks": [{"name": c.name, "passed": c.passed, "message": c.message}
                               for c in vresult.gate_checks],
                "judge_score": vresult.judge_report.overall_score if vresult.judge_report else None,
                "submittable": vresult.submittable,
                "failures": vresult.failures,
                "warnings": vresult.warnings,
            }

            if not vresult.submittable:
                a.finalize(Outcome.FAILED, cost=a.cost,
                           error=f"Verification failed (gate={vresult.gate_passed}, score={vresult.score:.2f}): {'; '.join(vresult.failures)}")
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

            # Step 6: Record skills (use correct vocabulary)
            a.metadata["skills_requested"] = plan.capabilities.required if plan.capabilities else []
            a.metadata["skills_installed"] = plan.skills_installed
            a.metadata["skills_activated"] = (plan.capabilities.already_available +
                                              [ac.name for ac in plan.acquisitions])

            # Step 7: Check immediate status (some platforms settle instantly)
            status = await adapter.check_status(opp)
            self.apply_status(a, status)

            # Step 8: Create WorkRun → Moltwork (private run only — no receipt/product yet)
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
        """Create WorkRun and send to Moltwork (private run only)."""
        import hashlib
        import httpx
        from get_me_money.workrun import WorkRun

        # Hash actual artifacts, not just metadata
        content = result.get("content", "")
        artifact_hash = hashlib.sha256(content.encode()).hexdigest() if content else ""

        run = WorkRun(
            job_title=opp.title,
            job_description=opp.description[:500],
            job_platform=opp.platform.value,
            job_external_id=opp.external_id,
            job_reward=opp.reward,
            agent_id=self.config.platforms.moltwork_worker_id,
            category=opp.category.value,
            tags=opp.tags + a.metadata.get("skills_activated", []),
            artifact_content=content,
            artifact_files=result.get("artifacts", []),
            verification_score=a.metadata.get("verification", {}).get("gate_score", 0),
            verification_passed=a.metadata.get("verification", {}).get("submittable", False),
            tokens_in=a.metadata.get("usage", {}).get("input_tokens", 0),
            tokens_out=a.metadata.get("usage", {}).get("output_tokens", 0),
            total_cost=a.cost,
            duration_seconds=a.duration_seconds,
            submitted=bool(a.submission_url),
            submission_url=a.submission_url,
            outcome=a.outcome.value,
            reward_earned=a.reward,
            skills_activated=a.metadata.get("skills_activated", []),
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
