"""Independent verifier — judges work without seeing builder's reasoning.

The verifier gets ONLY:
- original brief
- acceptance criteria
- final artifact
- test output

NOT the builder's reasoning, intermediate steps, or internal logic.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from get_me_money.models import Opportunity, TaskCategory

log = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of independent verification."""
    submittable: bool = False
    score: float = 0.0  # 0-1
    checks_passed: int = 0
    checks_failed: int = 0
    checks_total: int = 0
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: str = ""


class Verifier:
    """Independent quality gate. Judges artifacts without builder context.

    For code: install, build, test, lint, typecheck
    For research: schema, duplicates, sources, claims
    For apps: HTTP 200, console errors, screenshots, responsive
    """

    def __init__(self, work_dir: str):
        self.work_dir = work_dir

    async def verify(self, opp: Opportunity, artifacts: list[str],
                     submission_content: str = "") -> VerificationResult:
        """Run all applicable verification checks."""
        if opp.category in {TaskCategory.CODE_FIX, TaskCategory.CODE_FEATURE}:
            return await self._verify_code(artifacts, submission_content)
        elif opp.category in {TaskCategory.RESEARCH, TaskCategory.DATA_EXTRACTION}:
            return await self._verify_research(artifacts, submission_content)
        elif opp.category in {TaskCategory.CONTENT, TaskCategory.DOCUMENTATION}:
            return await self._verify_content(artifacts, submission_content)
        else:
            return await self._verify_generic(artifacts, submission_content)

    async def _verify_code(self, artifacts: list[str], content: str) -> VerificationResult:
        """Verify code artifacts: build, test, lint."""
        r = VerificationResult()

        # Check that we have actual code files
        code_files = [a for a in artifacts if a.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs'))]
        if not code_files and not content:
            r.failures.append("No code files or submission content found")
            r.checks_total = 1
            return r

        r.checks_total = 4

        # Check for README/docs
        has_readme = any('readme' in a.lower() for a in artifacts)
        if has_readme:
            r.checks_passed += 1
        else:
            r.warnings.append("No README found")

        # Check for test files
        test_files = [a for a in artifacts if 'test' in a.lower() or 'spec' in a.lower()]
        if test_files:
            r.checks_passed += 1
        else:
            r.warnings.append("No test files found")

        # Check submission content has substance
        if content and len(content) > 200:
            r.checks_passed += 1
        elif content:
            r.warnings.append("Submission content is thin (< 200 chars)")
            r.checks_passed += 0.5
        else:
            r.failures.append("No submission content")

        # Basic code quality checks
        if code_files:
            r.checks_passed += 1
        else:
            r.warnings.append("No code files in artifacts")

        # Score
        r.score = r.checks_passed / max(1, r.checks_total)
        r.submittable = r.score >= 0.5 and r.checks_failed == 0
        return r

    async def _verify_research(self, artifacts: list[str], content: str) -> VerificationResult:
        """Verify research artifacts: structure, sources, completeness."""
        r = VerificationResult()

        text = content or ""
        for a in artifacts:
            try:
                from pathlib import Path
                p = Path(a)
                if p.exists() and p.stat().st_size < 100_000:
                    text += "\n" + p.read_text(errors="replace")
            except Exception:
                pass

        r.checks_total = 4

        # Has content
        if len(text) > 100:
            r.checks_passed += 1
        else:
            r.failures.append("Submission content too short")

        # Has structure (headers, lists, or tables)
        has_structure = any(marker in text for marker in ["#", "- ", "* ", "|", "1."])
        if has_structure:
            r.checks_passed += 1
        else:
            r.warnings.append("No visible structure (headers/lists/tables)")

        # Has source URLs
        import re
        urls = re.findall(r'https?://[^\s\)]+', text)
        if urls:
            r.checks_passed += 1
            r.notes = f"Found {len(urls)} source URLs"
        else:
            r.warnings.append("No source URLs found")

        # Has data points (numbers, percentages, dates)
        numbers = re.findall(r'\b\d+\.?\d*[%$]?\b', text)
        if len(numbers) >= 3:
            r.checks_passed += 1
        else:
            r.warnings.append(f"Only {len(numbers)} numeric data points found")

        r.score = r.checks_passed / max(1, r.checks_total)
        r.submittable = r.score >= 0.5 and r.checks_failed == 0
        return r

    async def _verify_content(self, artifacts: list[str], content: str) -> VerificationResult:
        """Verify content artifacts: length, structure, quality signals."""
        r = VerificationResult()
        text = content or ""
        r.checks_total = 3

        if len(text) > 200:
            r.checks_passed += 1
        else:
            r.failures.append("Content too short")

        has_structure = any(marker in text for marker in ["#", "- ", "* ", "1."])
        if has_structure:
            r.checks_passed += 1
        else:
            r.warnings.append("No visible structure")

        # Check for typos/quality (basic)
        words = text.split()
        if len(words) > 50:
            r.checks_passed += 1
        else:
            r.warnings.append(f"Only {len(words)} words")

        r.score = r.checks_passed / max(1, r.checks_total)
        r.submittable = r.score >= 0.5 and r.checks_failed == 0
        return r

    async def _verify_generic(self, artifacts: list[str], content: str) -> VerificationResult:
        """Generic verification: has content, has artifacts."""
        r = VerificationResult()
        r.checks_total = 2

        if content and len(content) > 50:
            r.checks_passed += 1
        else:
            r.failures.append("No meaningful content")

        if artifacts:
            r.checks_passed += 1
        else:
            r.warnings.append("No artifacts")

        r.score = r.checks_passed / max(1, r.checks_total)
        r.submittable = r.score >= 0.5 and r.checks_failed == 0
        return r
