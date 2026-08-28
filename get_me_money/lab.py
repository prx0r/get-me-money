"""Lab mode: offline submission testing with exemplar fixtures.

Usage:
  moltwork lab run examples/x402-products
  moltwork lab run examples/x402-products --revisions 2

No wallet, no marketplace adapter, no external submission.
Just: task → spec → plan → build → judge → revise → record.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict
from pathlib import Path

from get_me_money.config import Config
from get_me_money.hermes_runtime import HermesRunner
from get_me_money.jobspec import JobSpec, WinPlan, parse_jobspec_from_hermes, parse_winplan_from_hermes
from get_me_money.models import Evaluation, Opportunity, Platform
from get_me_money.submission_run import SubmissionRun, CandidateRecord
from get_me_money.verifier import Verifier

log = logging.getLogger(__name__)


async def lab_run(fixture_dir: Path, config: Config, max_revisions: int = 1) -> SubmissionRun:
    """Run the full loop on an offline fixture."""
    run = SubmissionRun()

    # Load task
    task_file = fixture_dir / "task.md"
    if not task_file.exists():
        raise FileNotFoundError(f"No task.md in {fixture_dir}")
    task_text = task_file.read_text()
    run.task_title = task_text.split("\n")[0].lstrip("# ").strip()
    run.task_description = task_text
    run.task_platform = "lab"

    log.info(f"=== LAB RUN: {run.task_title[:60]} ===")

    # Step 1: Generate JobSpec
    log.info("Step 1: Generating JobSpec...")
    jobspec = await _generate_jobspec(config, run)
    run.jobspec = jobspec.to_dict()
    log.info(f"JobSpec: {len(jobspec.hard_requirements)} reqs, {len(jobspec.automatic_rejection)} rejection conditions")

    # Step 2: Generate WinPlan
    log.info("Step 2: Generating WinPlan...")
    winplan = await _generate_winplan(config, run, jobspec)
    run.strategy_differentiator = winplan.differentiation
    run.candidate_count = winplan.candidate_count
    run.revision_rounds = min(winplan.revision_rounds, max_revisions)
    log.info(f"WinPlan: candidates={run.candidate_count} revisions={run.revision_rounds}")

    # Step 3-5: Build + Judge + Revise
    best_candidate = None
    judge_feedback = ""

    for round_num in range(run.revision_rounds + 1):
        log.info(f"--- Round {round_num} ---")

        # Build
        log.info("Building candidate...")
        candidate = await _build_candidate(config, run, jobspec, winplan, round_num, judge_feedback)
        candidate.compute_hash()
        log.info(f"Candidate v{candidate.version}: {len(candidate.content)} chars, hash={candidate.content_hash}")

        # Judge
        log.info("Judging candidate...")
        verifier = Verifier(str(fixture_dir), jobspec=jobspec.to_dict(), config=config)
        opp = Opportunity(
            id="lab", platform=Platform.TASKMARKET, external_id="",
            title=run.task_title, description=run.task_description,
            reward=run.task_reward, currency="USDC",
        )
        vresult = await verifier.verify(opp, candidate.artifact_paths, candidate.content, jobspec=jobspec.to_dict())

        candidate.gate_passed = vresult.gate_passed
        candidate.judge_score = vresult.score
        candidate.submittable = vresult.submittable
        candidate.failures = vresult.failures
        candidate.warnings = vresult.warnings

        if vresult.judge_report:
            candidate.revision_feedback = "; ".join(vresult.judge_report.revision_suggestions)

        run.candidates.append(candidate)
        log.info(f"Judge: gate={vresult.gate_passed} score={vresult.score:.2f} submittable={vresult.submittable}")

        if vresult.submittable:
            best_candidate = candidate
            run.selected_candidate_version = candidate.version
            log.info("APPROVED")
            break

        # Prepare revision feedback
        judge_feedback = candidate.revision_feedback or "; ".join(vresult.failures)
        best_candidate = candidate  # keep best even if not approved

    if best_candidate and not best_candidate.submittable:
        run.selected_candidate_version = best_candidate.version
        log.info(f"Best candidate v{best_candidate.version} not approved, saving anyway")

    # Save
    run.completed_at = time.time()
    run.model = config.hermes.model or "unknown"
    run_dir = fixture_dir / "runs" / f"run-{int(time.time())}"
    run.save(run_dir)
    log.info(f"Saved: {run_dir}")

    # Save candidate content
    if best_candidate:
        (run_dir / "submission.md").write_text(best_candidate.content)

    return run


async def _generate_jobspec(config: Config, run: SubmissionRun) -> JobSpec:
    prompt = f"""Analyze this task and produce a JSON JobSpec.

TASK: {run.task_title}
DESCRIPTION:
{run.task_description[:3000]}

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
- Extract EVERY explicit requirement
- scoring weights sum to 1.0
- rejection conditions must be specific and testable
- Return ONLY the JSON"""

    opp = Opportunity(id="jobspec", platform=Platform.TASKMARKET, external_id="",
                      title="JobSpec analysis", description=prompt,
                      reward=0, currency="USDC")
    ev = Evaluation(opportunity_id="jobspec", probability_of_success=0.5, ev_cash=0, estimated_cost=0.01)
    runner = HermesRunner(config)
    result = await runner.run(opp, ev)
    return parse_jobspec_from_hermes(result.get("content", ""))


async def _generate_winplan(config: Config, run: SubmissionRun, jobspec: JobSpec) -> WinPlan:
    prompt = f"""Create a WinPlan for this task.

TASK: {run.task_title}
JOBSPEC:
{jobspec.to_prompt()}

Produce ONLY a JSON object:
{{
  "entry_decision": "Enter or Skip with reason",
  "differentiation": "strategy to stand out",
  "key_criteria": ["highest leverage criterion"],
  "risk_factors": ["risk 1"],
  "candidate_count": 1,
  "revision_rounds": 1
}}"""

    opp = Opportunity(id="winplan", platform=Platform.TASKMARKET, external_id="",
                      title="WinPlan", description=prompt,
                      reward=0, currency="USDC")
    ev = Evaluation(opportunity_id="winplan", probability_of_success=0.5, ev_cash=0, estimated_cost=0.01)
    runner = HermesRunner(config)
    result = await runner.run(opp, ev)
    return parse_winplan_from_hermes(result.get("content", ""))


async def _build_candidate(
    config: Config, run: SubmissionRun, jobspec: JobSpec, winplan: WinPlan,
    round_num: int, revision_feedback: str = "",
) -> CandidateRecord:
    candidate = CandidateRecord(version=round_num + 1)

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

    prompt = f"""{run.task_description}

--- HOW TO APPROACH ---
{approach}
--- END ---

DO THE ACTUAL WORK. Write deliverables to files. Write final submission to SUBMISSION.md."""

    opp = Opportunity(id=f"build-v{round_num+1}", platform=Platform.TASKMARKET, external_id="",
                      title=run.task_title, description=prompt,
                      reward=run.task_reward, currency="USDC")
    ev = Evaluation(opportunity_id=f"build-v{round_num+1}", probability_of_success=0.5, ev_cash=0, estimated_cost=0.01)

    runner = HermesRunner(config)
    result = await runner.run(opp, ev)

    candidate.content = result.get("content", "")
    candidate.artifact_paths = result.get("artifacts", [])
    return candidate
