"""Core submission loop — the invariant foundation for all agent specializations.

Given a bounty → produce the best possible submission → record everything.

This is the ONE loop. Specializations are configurations:
  - Coding agent: different skills, different judge rubric
  - Research agent: different skills, different judge rubric
  - Design agent: different skills, different judge rubric

The loop itself never changes:
  1. Understand task   (JobSpec)
  2. Plan approach     (WinPlan)
  3. Build candidate   (Hermes execution)
  4. Judge quality     (Gate + Judge)
  5. Revise if needed  (max N rounds)
  6. Submit            (adapter)
  7. Record            (SubmissionRun)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from get_me_money.config import Config
from get_me_money.hermes_runtime import HermesRunner, HermesError
from get_me_money.jobspec import JobSpec, WinPlan, parse_jobspec_from_hermes, parse_winplan_from_hermes
from get_me_money.models import Attempt, Evaluation, Opportunity, Outcome, Platform
from get_me_money.platforms import BaseAdapter
from get_me_money.submission_run import SubmissionRun, CandidateRecord
from get_me_money.verifier import Verifier, VerificationResult

log = logging.getLogger(__name__)

DEFAULT_MAX_REVISIONS = 2
HERMES_TIMEOUT = 180  # seconds per hermes call


@dataclass
class LoopResult:
    """Result of one full submission loop."""
    run: SubmissionRun | None = None
    attempt: Attempt | None = None
    submitted: bool = False
    error: str = ""


async def run_submission_loop(
    config: Config,
    opp: Opportunity,
    ev: Evaluation,
    adapter: BaseAdapter | None,
    work_dir: Path,
    max_revisions: int = DEFAULT_MAX_REVISIONS,
    skip_submit: bool = False,
) -> LoopResult:
    """The core loop. Given a bounty, produce the best submission.

    Steps:
      1. JobSpec   — understand what the task requires
      2. WinPlan   — decide how to approach it
      3. Build     — Hermes executes the work
      4. Judge     — deterministic gate + quality check
      5. Revise    — if judge fails, rebuild with feedback
      6. Submit    — only after judge passes (unless skip_submit)
      7. Record    — save SubmissionRun
    """
    run = SubmissionRun(
        task_title=opp.title,
        task_description=opp.description[:2000],
        task_reward=opp.reward,
        task_platform=opp.platform.value,
        task_id=opp.external_id,
    )
    result = LoopResult(run=run)

    t0 = time.time()

    # ── Step 1: Generate JobSpec ──────────────────────────────────────────
    log.info(f"[{run.task_title[:40]}] Step 1: JobSpec...")
    t1 = time.time()
    jobspec = _fallback_jobspec(opp)  # start with fallback
    try:
        candidate_spec = await asyncio.wait_for(
            _generate_jobspec(config, opp), timeout=HERMES_TIMEOUT
        )
        # Validate — reject empty/invalid specs
        if (candidate_spec.objective and
            candidate_spec.hard_requirements and
            candidate_spec.scoring and
            sum(candidate_spec.scoring.values()) > 0.5):
            jobspec = candidate_spec
            log.info(f"  JobSpec done ({time.time()-t1:.0f}s): {len(jobspec.hard_requirements)} reqs")
        else:
            log.warning(f"  JobSpec invalid, using fallback")
    except (asyncio.TimeoutError, Exception) as e:
        log.warning(f"  JobSpec failed: {e}, using fallback")
    run.jobspec = jobspec.to_dict()

    # ── Step 2: Generate WinPlan ──────────────────────────────────────────
    log.info(f"[{run.task_title[:40]}] Step 2: WinPlan...")
    t2 = time.time()
    try:
        winplan = await asyncio.wait_for(
            _generate_winplan(config, opp, jobspec), timeout=HERMES_TIMEOUT
        )
        run.strategy_differentiator = winplan.differentiation
        run.revision_rounds = min(winplan.revision_rounds, max_revisions)
        log.info(f"  WinPlan done ({time.time()-t2:.0f}s): {winplan.entry_decision[:50]}...")
    except asyncio.TimeoutError:
        log.warning("  WinPlan timed out, using defaults")
        winplan = WinPlan(entry_decision="Enter — default", candidate_count=1, revision_rounds=1)
    except Exception as e:
        log.warning(f"  WinPlan failed: {e}, using defaults")
        winplan = WinPlan(entry_decision="Enter — default", candidate_count=1, revision_rounds=1)

    # Check skip
    if "skip" in winplan.entry_decision.lower()[:20]:
        log.info(f"  SKIP: {winplan.entry_decision}")
        run.completed_at = time.time()
        result.attempt = Attempt(
            opportunity_id=opp.id, platform=opp.platform, external_id=opp.external_id,
            title=opp.title,
        )
        result.attempt.finalize(Outcome.SKIPPED, error=winplan.entry_decision)
        return result

    # ── Step 2.5: Check execution_mode ──────────────────────────────────
    from get_me_money.models import ExecutionMode
    if opp.execution_mode == ExecutionMode.HUMAN_INVOLVED:
        log.info(f"  HUMAN_INVOLVED — agent produces, human handles gates")
        if opp.has_human_gates:
            log.info(f"    Gates: {', '.join(g.stage for g in opp.human_gates)}")

    # ── Step 3-5: Build + Judge + Revise ──────────────────────────────────
    # Bound counts — LLM never gets authority over spending ceiling
    MAX_CANDIDATES = 5
    MAX_REVISIONS = 3
    num_candidates = max(1, min(winplan.candidate_count, MAX_CANDIDATES))
    max_revisions = max(0, min(winplan.revision_rounds - 1, MAX_REVISIONS))
    best_candidate = None
    judge_feedback = ""

    # Phase A: Build N independent candidates
    log.info(f"  Building {num_candidates} candidate(s)...")
    for ci in range(num_candidates):
        candidate_dir = work_dir / f"candidate-{ci}"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        t3 = time.time()

        candidate = CandidateRecord(version=ci + 1)
        try:
            suffix = f"\n\nVARIATION {ci+1}/{num_candidates}: Produce a distinctly different approach."
            build_result = await asyncio.wait_for(
                _build_candidate(config, opp, jobspec, winplan, candidate_dir,
                                "", suffix if ci > 0 else ""),
                timeout=HERMES_TIMEOUT * 2,
            )
            candidate.content = build_result.get("content", "")
            candidate.artifact_paths = build_result.get("artifacts", [])
            candidate.compute_hash()
            log.info(f"  Candidate v{ci+1} ({time.time()-t3:.0f}s): "
                     f"{len(candidate.content)} chars")
        except asyncio.TimeoutError:
            log.warning(f"  Candidate v{ci+1} timed out")
        except HermesError as e:
            log.error(f"  Candidate v{ci+1} failed: {e}")

        if not candidate.content or len(candidate.content) < 50:
            candidate.failures.append("No usable content produced")
        run.candidates.append(candidate)

    # Phase B: Blind judge all candidates
    log.info(f"  Judging {len(run.candidates)} candidate(s)...")
    for candidate in run.candidates:
        if not candidate.content or len(candidate.content) < 50:
            continue
        t4 = time.time()
        jdir = str(work_dir / f"candidate-{candidate.version - 1}")
        judge_result = await _judge_candidate(config, opp, jobspec, candidate.content, candidate.artifact_paths, jdir)
        candidate.gate_passed = judge_result.gate_passed
        candidate.judge_score = judge_result.score
        candidate.submittable = judge_result.submittable
        candidate.failures = judge_result.failures
        candidate.warnings = judge_result.warnings
        candidate.revision_feedback = "; ".join(
            (judge_result.judge_report.revision_suggestions if judge_result.judge_report else []) +
            judge_result.failures
        )
        log.info(f"  v{candidate.version}: gate={judge_result.gate_passed} "
                 f"score={judge_result.score:.2f} submittable={judge_result.submittable}")

    # Phase C: Select best by judge score
    scored = [c for c in run.candidates if c.judge_score > 0]
    if scored:
        best_candidate = max(scored, key=lambda c: c.judge_score)
        run.selected_candidate_version = best_candidate.version
        log.info(f"  Selected v{best_candidate.version} (score={best_candidate.judge_score:.2f})")

        # Phase D: Revise best if not submittable
        if not best_candidate.submittable and max_revisions > 0:
            judge_feedback = best_candidate.revision_feedback
            for rev in range(max_revisions):
                rev_dir = work_dir / f"revision-{rev}"
                rev_dir.mkdir(parents=True, exist_ok=True)
                log.info(f"  Revising (round {rev+1})...")

                rev_c = CandidateRecord(version=len(run.candidates) + 1)
                try:
                    br = await asyncio.wait_for(
                        _build_candidate(config, opp, jobspec, winplan, rev_dir, judge_feedback),
                        timeout=HERMES_TIMEOUT * 2,
                    )
                    rev_c.content = br.get("content", "")
                    rev_c.artifact_paths = br.get("artifacts", [])
                    rev_c.compute_hash()
                except Exception as e:
                    log.warning(f"  Revision failed: {e}")
                    continue

                if not rev_c.content or len(rev_c.content) < 50:
                    continue

                jr = await _judge_candidate(config, opp, jobspec, rev_c.content, rev_c.artifact_paths, str(rev_dir))
                rev_c.gate_passed = jr.gate_passed
                rev_c.judge_score = jr.score
                rev_c.submittable = jr.submittable
                rev_c.failures = jr.failures
                rev_c.revision_feedback = "; ".join(
                    (jr.judge_report.revision_suggestions if jr.judge_report else []) + jr.failures
                )
                run.candidates.append(rev_c)
                log.info(f"  Revision v{rev_c.version}: score={jr.score:.2f}")

                if jr.submittable or jr.score > best_candidate.judge_score:
                    best_candidate = rev_c
                    run.selected_candidate_version = rev_c.version
                    if jr.submittable:
                        log.info(f"  Revision approved v{rev_c.version}")
                        break
                judge_feedback = rev_c.revision_feedback

    # ── Step 6: Submit ────────────────────────────────────────────────────
    if best_candidate and best_candidate.submittable and adapter and not skip_submit:
        log.info(f"[{run.task_title[:40]}] Step 6: Submit...")
        try:
            submission = await adapter.submit(opp, {
                "content": best_candidate.content,
                "artifacts": best_candidate.artifact_paths,
            })
            if submission.get("ok"):
                run.external_status = "pending"
                result.submitted = True
                log.info(f"  Submitted: {submission.get('submission_id', '?')}")
            else:
                log.warning(f"  Submit failed: {submission.get('error', '?')}")
        except Exception as e:
            log.warning(f"  Submit error: {e}")

    # ── Step 6.5: Human gates ────────────────────────────────────────────
    if opp.has_human_gates and result.submitted:
        remaining_gates = [g for g in opp.human_gates if g.stage not in ("registration",)]
        if remaining_gates:
            log.info(f"  PAUSE: {len(remaining_gates)} human gate(s) remaining")
            for gate in remaining_gates:
                log.info(f"    → {gate.stage}: {gate.reason}")
            run.external_status = "paused_human"

    # ── Step 7: Record ────────────────────────────────────────────────────
    run.completed_at = time.time()
    run.total_cost = sum(
        float(c.metadata.get("cost", 0) or 0)
        for c in run.candidates
        if hasattr(c, "metadata")
    )
    run.selected_candidate_version = best_candidate.version if best_candidate else 0

    # Save run
    run_dir = work_dir / "runs" / f"run-{int(time.time())}"
    run.save(run_dir)
    if best_candidate:
        (run_dir / "submission.md").write_text(best_candidate.content)

    # Save attempt for ledger compatibility
    result.attempt = Attempt(
        opportunity_id=opp.id, platform=opp.platform, external_id=opp.external_id,
        title=opp.title, metadata={"run_dir": str(run_dir)},
    )
    if result.submitted:
        result.attempt.outcome = Outcome.PENDING
    else:
        result.attempt.finalize(Outcome.FAILED, cost=0, error="Judge did not approve" if best_candidate else "No candidate produced")

    elapsed = time.time() - t0
    log.info(f"[{run.task_title[:40]}] Done ({elapsed:.0f}s): "
             f"submitted={result.submitted} candidates={len(run.candidates)} "
             f"selected=v{run.selected_candidate_version}")

    # ── Step 8: Supply Chain — produce Parts + Products from this run ─────
    if best_candidate and best_candidate.submittable:
        try:
            from get_me_money.supply_chain import SupplyChain
            sc = SupplyChain(work_dir.parent.parent / "supply")
            sc.from_submission_run({
                "id": run.id if hasattr(run, "id") else f"run-{int(time.time())}",
                "task_title": run.task_title,
                "category": run.jobspec.get("deliverable_format", "mixed") if run.jobspec else "mixed",
                "content": best_candidate.content,
                "judge_score": best_candidate.judge_score,
                "accepted": False,  # never assume accepted — only external outcome can confirm
                "total_cost": run.total_cost,
                "reward": run.task_reward,
                "skills_used": run.jobspec.get("skills_required", []) if run.jobspec else [],
            })
            log.info(f"  Supply chain: product recorded")
        except Exception as e:
            log.warning(f"  Supply chain failed: {e}")

    # ── Step 9: Oracle Observation — feed market intelligence ─────────────
    if run.completed_at:
        try:
            from get_me_money.oracle_bridge import submit_to_oracle
            await submit_to_oracle({
                "id": f"run-{int(time.time())}",
                "task_title": run.task_title,
                "task_reward": run.task_reward,
                "category": run.jobspec.get("deliverable_format", "mixed") if run.jobspec else "mixed",
                "external_status": "submitted" if result.submitted else "failed",
                "judge_score": best_candidate.judge_score if best_candidate else 0,
                "total_cost": run.total_cost,
                "strategy_version": "default-v1",
                "skills_used": run.jobspec.get("skills_required", []) if run.jobspec else [],
            })
            log.info(f"  Oracle: observation submitted")
        except Exception as e:
            log.warning(f"  Oracle submission failed: {e}")

    return result


async def _generate_jobspec(config: Config, opp: Opportunity) -> JobSpec:
    prompt = f"""Analyze this task and produce a JSON JobSpec.

TASK: {opp.title}
DESCRIPTION: {opp.description[:3000]}
REWARD: {opp.reward} {opp.currency}

Produce ONLY a JSON object:
{{
  "objective": "one sentence",
  "hard_requirements": ["explicit requirement 1", ...],
  "scoring": {{"criterion": weight, ...}},
  "automatic_rejection": ["testable rejection condition 1", ...],
  "evidence_required": ["evidence type 1", ...],
  "deliverable_format": "markdown_files|code|report|mixed"
}}

Rules:
- Extract EVERY explicit requirement from the brief
- scoring weights sum to 1.0
- rejection conditions must be specific and testable
- Return ONLY the JSON object"""

    opp_copy = Opportunity(
        id=opp.id, platform=opp.platform, external_id=opp.external_id,
        title=opp.title, description=prompt,
        category=opp.category, reward=opp.reward, currency=opp.currency,
    )
    ev_copy = Evaluation(opportunity_id=opp.id, probability_of_success=0.5, ev_cash=0.5, estimated_cost=0.01)
    runner = HermesRunner(config)
    result = await runner.run(opp_copy, ev_copy)
    return parse_jobspec_from_hermes(result.get("content", ""))


def _fallback_jobspec(opp: Opportunity) -> JobSpec:
    return JobSpec(
        objective=opp.title,
        hard_requirements=["Complete the task as described", "Produce a SUBMISSION.md"],
        scoring={"completeness": 0.5, "quality": 0.5},
        automatic_rejection=["Empty submission", "Does not address the task"],
        evidence_required=["artifact_files"],
        deliverable_format="mixed",
    )


async def _generate_winplan(config: Config, opp: Opportunity, jobspec: JobSpec) -> WinPlan:
    prompt = f"""Create a WinPlan for this task.

TASK: {opp.title}
REWARD: {opp.reward} {opp.currency}
JOBSPEC OBJECTIVE: {jobspec.objective}
HARD REQUIREMENTS: {', '.join(jobspec.hard_requirements[:5])}
COMPETITION: {jobspec.competition}

Produce ONLY a JSON object:
{{
  "entry_decision": "Enter or Skip with reason",
  "differentiation": "strategy to stand out",
  "key_criteria": ["highest leverage criterion"],
  "candidate_count": 1,
  "revision_rounds": 1
}}"""

    opp_copy = Opportunity(
        id=opp.id, platform=opp.platform, external_id=opp.external_id,
        title=opp.title, description=prompt,
        category=opp.category, reward=opp.reward, currency=opp.currency,
    )
    ev_copy = Evaluation(opportunity_id=opp.id, probability_of_success=0.5, ev_cash=0.5, estimated_cost=0.01)
    runner = HermesRunner(config)
    result = await runner.run(opp_copy, ev_copy)
    return parse_winplan_from_hermes(result.get("content", ""))


async def _build_candidate(
    config: Config, opp: Opportunity, jobspec: JobSpec, winplan: WinPlan,
    work_dir: Path, revision_feedback: str = "", suffix: str = "",
) -> dict:
    approach = f"""
APPROACH THIS TASK WITH:

OBJECTIVE: {jobspec.objective}

HARD REQUIREMENTS (MUST satisfy ALL):
{chr(10).join(f'- {r}' for r in jobspec.hard_requirements)}

AUTOMATIC REJECTION:
{chr(10).join(f'- {r}' for r in jobspec.automatic_rejection)}

SCORING (what matters most):
{chr(10).join(f'- {k}: {v*100:.0f}%' for k, v in jobspec.scoring.items())}

DIFFERENTIATION: {winplan.differentiation}
KEY CRITERIA: {', '.join(winplan.key_criteria)}
"""
    if revision_feedback:
        approach += f"""
PREVIOUS VERSION WAS REJECTED. FIX THESE ISSUES:
{revision_feedback}
"""

    enriched = f"""{opp.description}

--- HOW TO APPROACH ---
{approach}
--- END ---

DO THE ACTUAL WORK. Write deliverables to files. Write final submission to SUBMISSION.md.{suffix}"""

    opp_enriched = Opportunity(
        id=opp.id, platform=opp.platform, external_id=opp.external_id,
        title=opp.title, description=enriched,
        category=opp.category, reward=opp.reward, currency=opp.currency,
    )
    ev = Evaluation(opportunity_id=opp.id, probability_of_success=0.5, ev_cash=0, estimated_cost=0.01)
    runner = HermesRunner(config, job_profile={"workspace": str(work_dir)})
    return await runner.run(opp_enriched, ev)


async def _judge_candidate(
    config: Config, opp: Opportunity, jobspec: JobSpec,
    content: str, artifacts: list[str], work_dir: str,
) -> VerificationResult:
    verifier = Verifier(work_dir, jobspec=jobspec.to_dict(), config=config)
    return await verifier.verify(opp, artifacts, content, jobspec=jobspec.to_dict())
