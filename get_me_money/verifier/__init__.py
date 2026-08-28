"""Two-phase verifier: deterministic gate + Hermes Judge.

Phase 1 (DeterministicGate): checks hard requirements from JobSpec.
  No LLM needed. MUST pass before Phase 2.

Phase 2 (Judge): Hermes evaluates quality against rubric.
  Sees ONLY: original task + JobSpec + artifact.
  Does NOT see: builder reasoning, intermediate steps.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class CheckResult:
    name: str = ""
    passed: bool = False
    message: str = ""


@dataclass
class JudgeReport:
    scores: dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    submittable: bool = False
    feedback: str = ""
    revision_suggestions: list[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    submittable: bool = False
    gate_passed: bool = False
    judge_report: JudgeReport | None = None
    gate_checks: list[CheckResult] = field(default_factory=list)
    gate_score: float = 0.0
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        return self.judge_report.overall_score if self.judge_report else self.gate_score

    @property
    def checks_passed(self) -> int:
        return sum(1 for c in self.gate_checks if c.passed)

    @property
    def checks_failed(self) -> int:
        return sum(1 for c in self.gate_checks if not c.passed)

    @property
    def checks_total(self) -> int:
        return len(self.gate_checks)


class DeterministicGate:
    """Phase 1: check hard requirements. No LLM."""

    def __init__(self, jobspec: dict | None = None):
        self.jobspec = jobspec or {}

    def check(self, work_dir: str, artifacts: list[str], content: str) -> list[CheckResult]:
        checks = [
            self._check_content_minimum(content),
            self._check_no_placeholders(content),
            self._check_no_todos(content),
        ]
        if self.jobspec:
            checks.extend(self._check_jobspec_requirements(artifacts, content))
        return checks

    def _check_content_minimum(self, content: str) -> CheckResult:
        if len(content) >= 100:
            return CheckResult(name="content_minimum", passed=True, message=f"{len(content)} chars")
        return CheckResult(name="content_minimum", passed=False, message=f"Only {len(content)} chars")

    def _check_no_placeholders(self, content: str) -> CheckResult:
        for p in [r"\[TODO\]", r"\[TBD\]", r"\[PLACEHOLDER\]", r"\{\{.*?\}\}", r"Lorem ipsum"]:
            if re.search(p, content, re.IGNORECASE):
                return CheckResult(name="no_placeholders", passed=False, message=f"Found: {p}")
        return CheckResult(name="no_placeholders", passed=True, message="Clean")

    def _check_no_todos(self, content: str) -> CheckResult:
        n = len(re.findall(r'\bTODO\b|\bFIXME\b|\bHACK\b', content, re.IGNORECASE))
        if n == 0:
            return CheckResult(name="no_todos", passed=True, message="Clean")
        return CheckResult(name="no_todos", passed=False, message=f"Found {n} TODO/FIXME/HACK")

    def _check_jobspec_requirements(self, artifacts: list[str], content: str) -> list[CheckResult]:
        checks = []
        for i, req in enumerate(self.jobspec.get("hard_requirements", [])):
            rl = req.lower()
            if "file" in rl and any(c.isdigit() for c in req):
                nums = re.findall(r'(\d+)', req)
                if nums:
                    expected = int(nums[0])
                    actual = len(artifacts)
                    op = ">=" if ("at least" in rl or ">=" in rl) else "=="
                    passed = actual >= expected if op == ">=" else actual == expected
                    checks.append(CheckResult(name=f"req_{i}_files", passed=passed,
                                              message=f"Expected {op} {expected}, got {actual}"))
            elif "source" in rl or "url" in rl or "citation" in rl:
                urls = re.findall(r'https?://[^\s\)]+', content)
                checks.append(CheckResult(name=f"req_{i}_urls", passed=len(urls) >= 1,
                                          message=f"{len(urls)} URLs"))
        return checks


class Judge:
    """Phase 2: Hermes-based quality evaluation."""

    def __init__(self, config=None):
        self.config = config

    async def evaluate(self, jobspec: dict, content: str, work_dir: str,
                       task_title: str = "", task_description: str = "") -> JudgeReport:
        """Use Hermes to judge the submission against the rubric."""
        if not self.config:
            return self._fallback_evaluate(jobspec, content)

        from get_me_money.hermes_runtime import HermesRunner
        from get_me_money.models import Evaluation, Opportunity, Platform

        scoring = jobspec.get("scoring", {})
        scoring_text = "\n".join(f"- {k}: {v*100:.0f}%" for k, v in scoring.items())
        rejection = jobspec.get("automatic_rejection", [])
        rejection_text = "\n".join(f"- {r}" for r in rejection)
        reqs = jobspec.get("hard_requirements", [])
        reqs_text = "\n".join(f"- {r}" for r in reqs)

        # Truncate content to fit in prompt
        truncated = content[:8000] if len(content) > 8000 else content

        judge_prompt = f"""You are an independent judge evaluating a submission. You do NOT see the builder's reasoning.

TASK: {task_title}

JOB SPECIFICATION:
Objective: {jobspec.get('objective', task_title)}

Hard Requirements:
{reqs_text}

Scoring Rubric:
{scoring_text}

Automatic Rejection:
{rejection_text}

SUBMISSION TO JUDGE:
---
{truncated}
---

Evaluate this submission. Return a JSON object:
{{
  "scores": {{"criterion_name": score_0_to_1, ...}},
  "overall_score": 0.0_to_1.0,
  "submittable": true_or_false,
  "feedback": "brief explanation",
  "revision_suggestions": ["specific improvement 1", "specific improvement 2"]
}}

Rules:
- Score each criterion 0.0 to 1.0 based on the rubric
- overall_score = weighted average using the rubric weights
- submittable = overall_score >= 0.6 AND no hard requirement violated
- Be honest. A score of 0.5 means mediocre. 0.8+ means genuinely good.
- revision_suggestions must be specific and actionable
- Return ONLY the JSON object"""

        opp = Opportunity(
            id="judge", platform=Platform.TASKMARKET, external_id="",
            title="Judge submission", description=judge_prompt,
            reward=0, currency="USDC",
        )
        ev = Evaluation(opportunity_id="judge", probability_of_success=0.5, ev_cash=0, estimated_cost=0.01)

        runner = HermesRunner(self.config)
        result = await runner.run(opp, ev)
        return self._parse_judge_response(result.get("content", ""), scoring)

    def _parse_judge_response(self, text: str, scoring: dict) -> JudgeReport:
        """Parse Hermes judge response into JudgeReport."""
        report = JudgeReport()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.S)
            if m:
                try:
                    data = json.loads(m.group(0))
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        report.scores = data.get("scores", {})
        report.overall_score = data.get("overall_score", 0.0)
        report.submittable = data.get("submittable", False)
        report.feedback = data.get("feedback", "")
        report.revision_suggestions = data.get("revision_suggestions", [])

        # Validate scores
        if not report.scores and scoring:
            # Fallback: the judge didn't return scores, use content analysis
            return self._fallback_evaluate({"scoring": scoring}, "")

        return report

    def _fallback_evaluate(self, jobspec: dict, content: str) -> JudgeReport:
        """Fallback when Hermes is unavailable."""
        report = JudgeReport()
        scoring = jobspec.get("scoring", {})
        if not scoring:
            scoring = {"completeness": 0.5, "quality": 0.5}

        total = 0.0
        for criterion, weight in scoring.items():
            score = min(1.0, len(content) / 2000) if content else 0.0
            report.scores[criterion] = score
            total += score * weight

        report.overall_score = total
        report.submittable = total >= 0.6 and len(content) >= 100
        return report


class Verifier:
    """Two-phase verification: deterministic gate + Hermes judge."""

    def __init__(self, work_dir: str, jobspec: dict | None = None, config=None):
        self.work_dir = work_dir
        self.gate = DeterministicGate(jobspec)
        self.judge = Judge(config)

    async def verify(self, opp, artifacts: list[str],
                     submission_content: str = "", jobspec: dict | None = None) -> VerificationResult:
        r = VerificationResult()

        # Phase 1: Deterministic gate
        effective_jobspec = jobspec or self.gate.jobspec
        self.gate = DeterministicGate(effective_jobspec)
        r.gate_checks = self.gate.check(self.work_dir, artifacts, submission_content)
        passed = sum(1 for c in r.gate_checks if c.passed)
        total = len(r.gate_checks)
        r.gate_score = passed / max(1, total)
        r.gate_passed = all(c.passed for c in r.gate_checks)

        if not r.gate_passed:
            r.failures = [f"{c.name}: {c.message}" for c in r.gate_checks if not c.passed]
            r.submittable = False
            return r

        # Phase 2: Hermes judge
        r.judge_report = await self.judge.evaluate(
            effective_jobspec, submission_content, self.work_dir,
            task_title=getattr(opp, "title", ""),
            task_description=getattr(opp, "description", ""),
        )
        r.submittable = r.judge_report.submittable
        if not r.submittable:
            r.failures.append(f"Judge score {r.judge_report.overall_score:.2f} < 0.6")
            if r.judge_report.feedback:
                r.warnings.append(r.judge_report.feedback)
            if r.judge_report.revision_suggestions:
                for s in r.judge_report.revision_suggestions:
                    r.warnings.append(f"Suggestion: {s}")

        return r
