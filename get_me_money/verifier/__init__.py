"""Two-phase verifier: deterministic gate + isolated LLM Judge.

Phase 1 (DeterministicGate): checks hard requirements from JobSpec.
  - File count, format, required sections, placeholder detection
  - No LLM needed. Pure Python. MUST pass before Phase 2.

Phase 2 (Judge): evaluates subjective quality against rubric.
  - Sees ONLY: original task, JobSpec, final artifacts.
  - Does NOT see: builder reasoning, intermediate steps, internal logic.
  - Returns rubric scores + pass/fail.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    """Combined result of deterministic gate + judge."""
    submittable: bool = False
    gate_passed: bool = False
    judge_report: JudgeReport | None = None
    gate_checks: list[CheckResult] = field(default_factory=list)
    gate_score: float = 0.0
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def score(self) -> float:
        if self.judge_report:
            return self.judge_report.overall_score
        return self.gate_score

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
    """Phase 1: check hard requirements from JobSpec. No LLM."""

    def __init__(self, jobspec: dict | None = None):
        self.jobspec = jobspec or {}

    def check(self, work_dir: str, artifacts: list[str], content: str) -> list[CheckResult]:
        """Run all deterministic checks against the JobSpec."""
        checks = []
        checks.append(self._check_content_minimum(content))
        checks.append(self._check_no_placeholders(content))
        checks.append(self._check_no_todos(content))

        # JobSpec-specific checks
        if self.jobspec:
            checks.extend(self._check_jobspec_requirements(work_dir, artifacts, content))

        return checks

    def _check_content_minimum(self, content: str) -> CheckResult:
        if len(content) >= 100:
            return CheckResult(name="content_minimum", passed=True, message=f"{len(content)} chars")
        return CheckResult(name="content_minimum", passed=False, message=f"Only {len(content)} chars, need 100+")

    def _check_no_placeholders(self, content: str) -> CheckResult:
        placeholders = [r"\[TODO\]", r"\[TBD\]", r"\[PLACEHOLDER\]", r"\{\{.*?\}\}",
                        r"INSERT.*HERE", r"Lorem ipsum", r"FIXME"]
        for p in placeholders:
            if re.search(p, content, re.IGNORECASE):
                return CheckResult(name="no_placeholders", passed=False, message=f"Found placeholder: {p}")
        return CheckResult(name="no_placeholders", passed=True, message="Clean")

    def _check_no_todos(self, content: str) -> CheckResult:
        todo_count = len(re.findall(r'\bTODO\b|\bFIXME\b|\bHACK\b', content, re.IGNORECASE))
        if todo_count == 0:
            return CheckResult(name="no_todos", passed=True, message="Clean")
        return CheckResult(name="no_todos", passed=False, message=f"Found {todo_count} TODO/FIXME/HACK markers")

    def _check_jobspec_requirements(self, work_dir: str, artifacts: list[str], content: str) -> list[CheckResult]:
        """Check JobSpec hard requirements."""
        checks = []
        reqs = self.jobspec.get("hard_requirements", [])

        for i, req in enumerate(reqs):
            req_lower = req.lower()
            # File count requirements
            if "file" in req_lower and any(c.isdigit() for c in req):
                nums = re.findall(r'(\d+)', req)
                if nums:
                    expected = int(nums[0])
                    actual = len(artifacts)
                    passed = actual >= expected if "at least" in req_lower or ">=" in req_lower else actual == expected
                    checks.append(CheckResult(
                        name=f"req_{i}_file_count",
                        passed=passed,
                        message=f"Expected {expected} files, got {actual}"
                    ))

            # Section/heading requirements
            elif "section" in req_lower or "heading" in req_lower or "include" in req_lower:
                # Extract quoted terms
                quoted = re.findall(r'["\']([^"\']+)["\']', req)
                for term in quoted:
                    found = term.lower() in content.lower()
                    checks.append(CheckResult(
                        name=f"req_{i}_has_{term[:20]}",
                        passed=found,
                        message=f"{'Found' if found else 'Missing'}: {term}"
                    ))

            # URL/source requirements
            elif "source" in req_lower or "url" in req_lower or "citation" in req_lower:
                urls = re.findall(r'https?://[^\s\)]+', content)
                passed = len(urls) >= 1
                checks.append(CheckResult(
                    name=f"req_{i}_sources",
                    passed=passed,
                    message=f"Found {len(urls)} URLs"
                ))

            # Numeric requirements
            elif re.search(r'\d+', req):
                # Generic numeric check — see if content mentions the number
                nums_in_req = re.findall(r'(\d+)', req)
                content_lower = content.lower()
                relevant_nums = [n for n in nums_in_req if n in content_lower]
                passed = len(relevant_nums) >= len(nums_in_req) // 2
                checks.append(CheckResult(
                    name=f"req_{i}_numeric",
                    passed=passed,
                    message=f"Found {len(relevant_nums)}/{len(nums_in_req)} required numbers"
                ))

        return checks


class Judge:
    """Phase 2: LLM-based quality evaluation. Isolated from builder reasoning."""

    def __init__(self):
        pass

    async def evaluate(self, jobspec: dict, content: str, work_dir: str) -> JudgeReport:
        """Evaluate submission quality against the JobSpec rubric.

        This method is a placeholder — the real judge will call Hermes
        to evaluate the submission against the rubric criteria.
        For now, return a basic report based on content analysis.
        """
        report = JudgeReport()

        # Extract scoring criteria from jobspec
        scoring = jobspec.get("scoring", {})
        if not scoring:
            # Default rubric
            scoring = {
                "completeness": 0.3,
                "accuracy": 0.3,
                "quality": 0.2,
                "presentation": 0.2,
            }

        # Basic content analysis for each criterion
        total = 0.0
        for criterion, weight in scoring.items():
            score = self._score_criterion(criterion, content)
            report.scores[criterion] = score
            total += score * weight

        report.overall_score = total

        # Check rejection conditions
        rejection = jobspec.get("automatic_rejection", [])
        for condition in rejection:
            if self._check_rejection_condition(condition, content):
                report.submittable = False
                report.feedback += f"REJECTED: {condition}\n"
                return report

        report.submittable = report.overall_score >= 0.5
        return report

    def _score_criterion(self, criterion: str, content: str) -> float:
        """Score a single criterion based on content analysis."""
        c = criterion.lower()
        words = content.split()
        word_count = len(words)

        if "completeness" in c or "thorough" in c:
            if word_count > 1000: return 0.9
            if word_count > 500: return 0.7
            if word_count > 200: return 0.5
            return 0.3

        if "original" in c or "creative" in c:
            # Check for unique terms vs generic language
            unique_ratio = len(set(words)) / max(1, word_count)
            return min(1.0, unique_ratio * 2)

        if "source" in c or "evidence" in c:
            urls = re.findall(r'https?://', content)
            return min(1.0, len(urls) * 0.2)

        if "quality" in c or "accura" in c:
            # Check for data points, structure
            has_numbers = len(re.findall(r'\d+', content)) > 3
            has_structure = any(m in content for m in ["#", "- ", "| "])
            score = 0.3
            if has_numbers: score += 0.3
            if has_structure: score += 0.3
            return min(1.0, score)

        if "present" in c or "format" in c:
            has_headers = bool(re.search(r'^#+\s', content, re.MULTILINE))
            has_lists = bool(re.search(r'^[-*]\s', content, re.MULTILINE))
            score = 0.3
            if has_headers: score += 0.35
            if has_lists: score += 0.35
            return min(1.0, score)

        # Default
        return 0.5

    def _check_rejection_condition(self, condition: str, content: str) -> bool:
        """Check if a rejection condition is triggered."""
        c = condition.lower()
        if "placeholder" in c or "todo" in c:
            return bool(re.search(r'TODO|FIXME|\[TBD\]|\{\{.*?\}\}', content, re.IGNORECASE))
        if "duplicate" in c:
            # Check for repeated paragraphs
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            if len(paragraphs) > 2:
                unique = set(paragraphs)
                return len(unique) < len(paragraphs) * 0.8
        if "missing" in c:
            # Check if something mentioned in the condition is absent
            terms = re.findall(r'["\']([^"\']+)["\']', condition)
            return any(t.lower() not in content.lower() for t in terms)
        return False


class Verifier:
    """Two-phase verification: deterministic gate + LLM judge."""

    def __init__(self, work_dir: str, jobspec: dict | None = None):
        self.work_dir = work_dir
        self.gate = DeterministicGate(jobspec)
        self.judge = Judge()

    async def verify(self, opp, artifacts: list[str],
                     submission_content: str = "", jobspec: dict | None = None) -> VerificationResult:
        """Run deterministic gate, then judge if gate passes."""
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

        # Phase 2: LLM judge
        r.judge_report = await self.judge.evaluate(
            effective_jobspec, submission_content, self.work_dir
        )
        r.submittable = r.judge_report.submittable
        if not r.submittable:
            r.failures.append(f"Judge score {r.judge_report.overall_score:.2f} below threshold")
            if r.judge_report.feedback:
                r.warnings.append(r.judge_report.feedback)

        return r
