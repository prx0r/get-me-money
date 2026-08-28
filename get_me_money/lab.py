"""Lab mode: offline submission testing with timestamped logging.

Every run is logged with:
  - timestamp
  - fixture name
  - JobSpec, WinPlan, candidates, judge reports
  - timing per step
  - review notes

Usage:
  moltwork lab run examples/x402-products
  moltwork lab run examples/research-bounty --revisions 2
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from get_me_money.config import Config
from get_me_money.loop import run_submission_loop, LoopResult
from get_me_money.submission_run import SubmissionRun

log = logging.getLogger(__name__)


async def lab_run(fixture_dir: Path, config: Config, max_revisions: int = 1) -> LoopResult:
    """Run the full loop on an offline fixture. Logs everything."""
    task_file = fixture_dir / "task.md"
    if not task_file.exists():
        raise FileNotFoundError(f"No task.md in {fixture_dir}")

    task_text = task_file.read_text()
    title = task_text.split("\n")[0].lstrip("# ").strip()

    # Create work dir
    work_dir = fixture_dir / "runs" / f"run-{int(time.time())}"
    work_dir.mkdir(parents=True, exist_ok=True)

    # Build opportunity from task
    from get_me_money.models import Evaluation, Opportunity, Platform
    opp = Opportunity(
        id=f"lab-{fixture_dir.name}",
        platform=Platform.TASKMARKET,
        external_id="",
        title=title,
        description=task_text,
        reward=0,
        currency="USD",
    )
    ev = Evaluation(
        opportunity_id=opp.id,
        probability_of_success=0.5,
        ev_cash=0,
        estimated_cost=0,
    )

    # Run the loop (no adapter = no submit)
    result = await run_submission_loop(
        config, opp, ev, adapter=None, work_dir=work_dir,
        max_revisions=max_revisions, skip_submit=True,
    )

    # Save run log
    if result.run:
        result.run.save(work_dir)

    # Save review
    review = _generate_review(result, fixture_dir.name)
    (work_dir / "review.md").write_text(review)

    # Save timing log
    timing = _extract_timing(result)
    (work_dir / "timing.json").write_text(json.dumps(timing, indent=2))

    return result


def _generate_review(result: LoopResult, fixture_name: str) -> str:
    """Generate a timestamped review of the run."""
    run = result.run
    lines = [
        f"# Lab Run Review",
        f"",
        f"**Fixture:** {fixture_name}",
        f"**Timestamp:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"**Submitted:** {result.submitted}",
        f"**Error:** {result.error or 'none'}",
        f"",
    ]

    if run:
        lines.extend([
            f"## Task",
            f"- Title: {run.task_title[:60]}",
            f"- Reward: ${run.task_reward:.2f}",
            f"- Platform: {run.task_platform}",
            f"",
            f"## JobSpec",
        ])
        if run.jobspec:
            lines.append(f"- Objective: {run.jobspec.get('objective', '?')[:80]}")
            lines.append(f"- Hard requirements: {len(run.jobspec.get('hard_requirements', []))}")
            lines.append(f"- Rejection conditions: {len(run.jobspec.get('automatic_rejection', []))}")
            lines.append(f"- Scoring: {run.jobspec.get('scoring', {})}")
        lines.append("")

        lines.extend([
            f"## Strategy",
            f"- Differentiation: {run.strategy_differentiator[:80] if run.strategy_differentiator else '?'}",
            f"- Candidates: {len(run.candidates)}",
            f"- Selected: v{run.selected_candidate_version}",
            f"",
            f"## Candidates",
        ])
        for c in run.candidates:
            lines.append(f"### v{c.version}")
            lines.append(f"- Content: {len(c.content)} chars, hash={c.content_hash}")
            lines.append(f"- Gate: {'PASS' if c.gate_passed else 'FAIL'}")
            lines.append(f"- Judge score: {c.judge_score:.2f}")
            lines.append(f"- Submittable: {c.submittable}")
            if c.failures:
                lines.append(f"- Failures: {'; '.join(c.failures)}")
            if c.revision_feedback:
                lines.append(f"- Revision feedback: {c.revision_feedback[:200]}")
            lines.append("")

        lines.extend([
            f"## External Outcome",
            f"- Status: {run.external_status or 'pending'}",
            f"- Score: {run.external_score or 'n/a'}",
            f"- Rank: {run.external_rank or 'n/a'}",
            f"- Feedback: {run.external_feedback or 'none'}",
            f"",
            f"## Learning",
            f"- Postmortem: {run.postmortem or 'pending outcome'}",
            f"- Lessons: {', '.join(run.lessons) if run.lessons else 'none yet'}",
            f"",
        ])

    # Review notes
    lines.extend([
        f"## Review Notes",
        f"",
    ])
    if result.submitted:
        lines.append("- Run completed successfully")
    elif result.run and result.run.candidates:
        best = max(result.run.candidates, key=lambda c: c.judge_score)
        if best.gate_passed and best.judge_score >= 0.6:
            lines.append("- Gate passed but judge did not approve")
        elif not best.gate_passed:
            lines.append("- Gate failed (hard requirements not met)")
        else:
            lines.append("- Judge score below threshold")
    else:
        lines.append("- No candidates produced (timeout or error)")

    if result.run and len(result.run.candidates) > 1:
        lines.append(f"- Revision improved score: v1={result.run.candidates[0].judge_score:.2f} → "
                     f"v{result.run.candidates[-1].version}={result.run.candidates[-1].judge_score:.2f}")

    return "\n".join(lines)


def _extract_timing(result: LoopResult) -> dict:
    """Extract timing information from the run."""
    timing = {"fixture": result.run.task_title[:40] if result.run else "?", "steps": []}
    if result.run and result.run.candidates:
        for c in result.run.candidates:
            timing["steps"].append({
                "version": c.version,
                "content_chars": len(c.content),
                "gate_passed": c.gate_passed,
                "judge_score": c.judge_score,
            })
    return timing
