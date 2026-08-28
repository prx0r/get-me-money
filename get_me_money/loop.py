"""Core submission loop — the invariant foundation for all agent specializations.

Given a bounty → produce the best possible submission → record everything.

This is the ONE loop. Specializations are configurations on top of it:
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
  7. Record            (WorkRun)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from get_me_money.config import Config
from get_me_money.hermes_runtime import HermesRunner, HermesError
from get_me_money.jobspec import JobSpec, WinPlan, parse_jobspec_from_hermes, parse_winplan_from_hermes
from get_me_money.models import Attempt, Evaluation, Opportunity, Outcome, Platform
from get_me_money.platforms import BaseAdapter
from get_me_money.verifier import Verifier, VerificationResult

log = logging.getLogger(__name__)

# Max revision rounds before giving up
MAX_REVISIONS = 2


@dataclass
class LoopResult:
    """Result of one full submission loop."""
    attempt: Attempt | None = None
    jobspec: JobSpec | None = None
    winplan: WinPlan | None = None
    candidate_count: int = 0
    revision_count: int = 0
    judge_reports: list[dict] = field(default_factory=list)
    submitted: bool = False
    error: str = ""


async def run_submission_loop(
    config: Config,
    opp: Opportunity,
    ev: Evaluation,
    adapter: BaseAdapter,
    work_dir: Path,
    max_revisions: int = MAX_REVISIONS,
) -> LoopResult:
    """The core loop. Given a bounty, produce the best submission.

    Steps:
      1. JobSpec   — understand what the task requires
      2. WinPlan   — decide how to approach it
      3. Build     — Hermes executes the work
      4. Judge     — deterministic gate + quality check
      5. Revise    — if judge fails, rebuild with feedback
      6. Submit    — only after judge passes
      7. Record    — save everything
    """
    result = LoopResult()
    a = Attempt(
        opportunity_id=opp.id, platform=opp.platform, external_id=opp.external_id,
        title=opp.title, metadata={
            "category": opp.category.value,
            "predicted_p": ev.probability_of_success,
            "predicted_cash_ev": ev.ev_cash,
            "reward_offered": opp.reward,
        },
    )

    # ── Step 1: Generate JobSpec ──────────────────────────────────────────
    log.info("Step 1: Generating JobSpec...")
    try:
        jobspec = await _generate_jobspec(config, opp, work_dir)
        result.jobspec = jobspec
        a.metadata["jobspec"] = jobspec.to_dict()
        log.info(f"JobSpec: {len(jobspec.hard_requirements)} hard requirements, "
                 f"{len(jobspec.automatic_rejection)} rejection conditions")
    except Exception as e:
        log.warning(f"JobSpec generation failed, using fallback: {e}")
        jobspec = _fallback_jobspec(opp)
        result.jobspec = jobspec
        a.metadata["jobspec"] = jobspec.to_dict()

    # ── Step 2: Generate WinPlan ──────────────────────────────────────────
    log.info("Step 2: Generating WinPlan...")
    try:
        winplan = await _generate_winplan(config, opp, jobspec, work_dir)
        result.winplan = winplan
        a.metadata["winplan"] = winplan.to_dict()
        log.info(f"WinPlan: {winplan.entry_decision[:60]}... "
                 f"candidates={winplan.candidate_count} revisions={winplan.revision_rounds}")
    except Exception as e:
        log.warning(f"WinPlan generation failed, using defaults: {e}")
        winplan = WinPlan(
            entry_decision="Enter — default plan",
            candidate_count=1,
            revision_rounds=max_revisions,
        )
        result.winplan = winplan

    # Check if we should even enter
    if "skip" in winplan.entry_decision.lower()[:20]:
        a.finalize(Outcome.SKIPPED, error=f"WinPlan says skip: {winplan.entry_decision}")
        result.attempt = a
        return result

    # ── Step 3-5: Build + Judge + Revise ──────────────────────────────────
    max_rounds = min(winplan.revision_rounds, max_revisions)
    best_content = ""
    best_artifacts: list[str] = []
    best_judge: VerificationResult | None = None
    judge_feedback = ""

    for round_num in range(max_rounds + 1):
        candidate_dir = work_dir / f"candidate-{round_num}"
        candidate_dir.mkdir(parents=True, exist_ok=True)

        # Step 3: Build candidate
        log.info(f"Step 3: Building candidate (round {round_num})...")
        try:
            build_result = await _build_candidate(
                config, opp, ev, jobspec, winplan, candidate_dir,
                revision_feedback=judge_feedback if round_num > 0 else "",
            )
            content = build_result.get("content", "")
            artifacts = build_result.get("artifacts", [])
            cost = float(build_result.get("cost", 0) or 0)
            a.cost += cost
            a.metadata[f"round_{round_num}_artifacts"] = artifacts
            a.metadata[f"round_{round_num}_cost"] = cost

            if not content or len(content) < 50:
                log.warning(f"Round {round_num}: Hermes produced no usable content")
                continue
        except HermesError as e:
            log.error(f"Round {round_num}: Hermes failed: {e}")
            a.cost += e.cost
            continue

        # Step 4: Judge quality
        log.info(f"Step 4: Judging candidate (round {round_num})...")
        judge_result = await _judge_candidate(
            config, opp, jobspec, content, artifacts, str(candidate_dir)
        )
        result.judge_reports.append({
            "round": round_num,
            "gate_passed": judge_result.gate_passed,
            "gate_score": judge_result.gate_score,
            "submittable": judge_result.submittable,
            "score": judge_result.score,
            "failures": judge_result.failures,
            "warnings": judge_result.warnings,
        })

        log.info(f"Round {round_num}: gate={judge_result.gate_passed} "
                 f"score={judge_result.score:.2f} submittable={judge_result.submittable}")

        if judge_result.submittable:
            best_content = content
            best_artifacts = artifacts
            best_judge = judge_result
            break

        # Prepare for revision
        judge_feedback = "; ".join(judge_result.failures + judge_result.warnings)
        result.revision_count += 1

        # Keep best so far even if not submittable
        if len(content) > len(best_content):
            best_content = content
            best_artifacts = artifacts
            best_judge = judge_result

    result.candidate_count = result.revision_count + 1

    # ── Step 6: Submit ────────────────────────────────────────────────────
    if best_judge and best_judge.submittable and best_content:
        log.info("Step 6: Submitting...")
        a.metadata["verification"] = {
            "gate_passed": best_judge.gate_passed,
            "gate_score": best_judge.gate_score,
            "judge_score": best_judge.judge_report.overall_score if best_judge.judge_report else None,
            "submittable": best_judge.submittable,
            "failures": best_judge.failures,
        }
        a.metadata["artifacts"] = best_artifacts
        a.metadata["content_preview"] = best_content[:500]

        try:
            submission = await adapter.submit(opp, {"content": best_content, "artifacts": best_artifacts})
            if submission.get("ok"):
                a.submission_url = str(submission.get("url", ""))
                a.outcome = Outcome.PENDING
                a.duration_seconds = time.time() - a.started_at
                result.submitted = True
                result.attempt = a
                log.info(f"Submitted: {a.submission_url[:60]}")
            else:
                a.finalize(Outcome.FAILED, cost=a.cost, error=submission.get("error", "submit failed"))
                result.attempt = a
        except Exception as e:
            a.finalize(Outcome.FAILED, cost=a.cost, error=f"Submit error: {e}")
            result.attempt = a
    else:
        reason = "No submittable candidate" if not best_judge else "Judge did not approve"
        a.finalize(Outcome.FAILED, cost=a.cost, error=reason)
        result.attempt = a

    return result


async def _generate_jobspec(config: Config, opp: Opportunity, work_dir: Path) -> JobSpec:
    """Use Hermes to analyze the task and produce a structured JobSpec."""
    prompt = f"""Analyze this task and produce a JSON JobSpec.

TASK TITLE: {opp.title}
TASK DESCRIPTION: {opp.description}
REWARD: {opp.reward} {opp.currency}
PLATFORM: {opp.platform.value}

Produce a JSON object with these fields:
{{
  "objective": "one sentence describing what must be produced",
  "hard_requirements": ["list of explicit requirements from the brief"],
  "scoring": {{"criterion": weight, ...}},
  "automatic_rejection": ["conditions that cause automatic rejection"],
  "evidence_required": ["what evidence must accompany the submission"],
  "deliverable_format": "markdown_files|code|report|mixed",
  "competition": {{"submissions": N, "difficulty": "low|medium|high"}}
}}

Rules:
- Extract EVERY explicit requirement from the brief
- scoring weights must sum to 1.0
- automatic_rejection must be specific and testable
- Do not invent requirements not in the original brief
- Return ONLY the JSON object, nothing else"""

    runner = HermesRunner(config)
    opp_copy = Opportunity(
        id=opp.id, platform=opp.platform, external_id=opp.external_id,
        title=f"JobSpec analysis: {opp.title}", description=prompt,
        category=opp.category, reward=opp.reward, currency=opp.currency,
    )
    ev_copy = Evaluation(opportunity_id=opp.id, probability_of_success=0.5, ev_cash=0.5, estimated_cost=0.01)
    result = await runner.run(opp_copy, ev_copy)
    return parse_jobspec_from_hermes(result.get("content", ""))


def _fallback_jobspec(opp: Opportunity) -> JobSpec:
    """Fallback JobSpec when hermes fails."""
    return JobSpec(
        objective=opp.title,
        hard_requirements=["Complete the task as described", "Produce a SUBMISSION.md"],
        scoring={"completeness": 0.5, "quality": 0.5},
        automatic_rejection=["Empty submission", "Does not address the task"],
        evidence_required=["artifact_files"],
        deliverable_format="mixed",
        source_title=opp.title,
        source_description=opp.description[:500],
    )


async def _generate_winplan(config: Config, opp: Opportunity, jobspec: JobSpec, work_dir: Path) -> WinPlan:
    """Use Hermes to analyze the JobSpec and produce a WinPlan."""
    prompt = f"""Given this JobSpec, create a WinPlan.

JOBSPEC:
{jobspec.to_prompt()}

REWARD: {opp.reward} {opp.currency}

Produce a JSON object:
{{
  "entry_decision": "Enter or Skip with brief reason",
  "differentiation": "what makes our submission stand out",
  "key_criteria": ["highest-leverage criteria to nail"],
  "risk_factors": ["things that could go wrong"],
  "estimated_effort_hours": 0.5,
  "candidate_count": 1,
  "revision_rounds": 1
}}

Rules:
- If reward < $1 and competition > 20 submissions, consider Skip
- candidate_count: 1 for objective tasks, 3 for subjective high-value
- revision_rounds: 1 for cheap tasks, 2 for expensive ones
- Return ONLY the JSON object, nothing else"""

    runner = HermesRunner(config)
    opp_copy = Opportunity(
        id=opp.id, platform=opp.platform, external_id=opp.external_id,
        title=f"WinPlan: {opp.title}", description=prompt,
        category=opp.category, reward=opp.reward, currency=opp.currency,
    )
    ev_copy = Evaluation(opportunity_id=opp.id, probability_of_success=0.5, ev_cash=0.5, estimated_cost=0.01)
    result = await runner.run(opp_copy, ev_copy)
    return parse_winplan_from_hermes(result.get("content", ""))


async def _build_candidate(
    config: Config, opp: Opportunity, ev: Evaluation,
    jobspec: JobSpec, winplan: WinPlan, work_dir: Path,
    revision_feedback: str = "",
) -> dict:
    """Execute the actual work via Hermes with full context."""
    # The opportunity description is the ACTUAL TASK.
    # JobSpec and WinPlan are CONTEXT for how to approach it.
    context = f"""
APPROACH THIS TASK USING THE FOLLOWING ANALYSIS:

OBJECTIVE: {jobspec.objective}

HARD REQUIREMENTS (you MUST satisfy ALL):
{chr(10).join(f'- {r}' for r in jobspec.hard_requirements)}

AUTOMATIC REJECTION (any of these = fail):
{chr(10).join(f'- {r}' for r in jobspec.automatic_rejection)}

DELIVERABLE FORMAT: {jobspec.deliverable_format}

SCORING CRITERIA (what the evaluator cares about):
{chr(10).join(f'- {k}: {v*100:.0f}%' for k, v in jobspec.scoring.items())}

DIFFERENTIATION STRATEGY: {winplan.differentiation}

KEY CRITERIA TO NAIL: {', '.join(winplan.key_criteria)}
"""
    if revision_feedback:
        context += f"""
PREVIOUS ATTEMPT WAS REJECTED. JUDGE FEEDBACK:
{revision_feedback}
IMPROVE based on this feedback.
"""

    # Keep the original task description but append the approach context
    enriched_desc = f"""{opp.description}

--- HOW TO APPROACH THIS TASK ---
{context}
--- END APPROACH ---

NOW DO THE ACTUAL WORK. Write your deliverables to files in the current directory.
Write your final submission to SUBMISSION.md.
Your last response must be a JSON object: {{"completed":true,"artifacts":["SUBMISSION.md"]}}"""

    opp_enriched = Opportunity(
        id=opp.id, platform=opp.platform, external_id=opp.external_id,
        title=opp.title, description=enriched_desc,
        category=opp.category, reward=opp.reward, currency=opp.currency,
        tags=opp.tags, url=opp.url, raw=opp.raw,
    )

    runner = HermesRunner(config)
    return await runner.run(opp_enriched, ev)


async def _judge_candidate(
    config: Config, opp: Opportunity, jobspec: JobSpec,
    content: str, artifacts: list[str], work_dir: str,
) -> VerificationResult:
    """Run deterministic gate + judge on the candidate."""
    verifier = Verifier(work_dir, jobspec=jobspec.to_dict())
    return await verifier.verify(opp, artifacts, content, jobspec=jobspec.to_dict())
