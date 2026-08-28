"""Repute — the system for winning tasks through rubric-based quality.

The difference between winning and losing:
- Losers submit generic slop
- Winners parse the rubric, build against every criterion, self-score, and only submit when ready

Repute:
1. Parses task → structured checklist
2. Scores work against checklist before submitting
3. Records outcomes → learns what scores well
4. Refuses to submit below quality threshold
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from get_me_money.config import DATA_DIR


CRITERIA_DB = DATA_DIR / "repute-criteria.jsonl"
OUTCOMES_DB = DATA_DIR / "repute-outcomes.jsonl"
STRATEGIES_DB = DATA_DIR / "repute-strategies.jsonl"


@dataclass
class Criterion:
    """One acceptance criterion extracted from a task."""
    id: str = ""
    description: str = ""
    weight: float = 1.0       # 0-1, how important
    verifiable: bool = False   # can we prove this with evidence?
    category: str = ""         # research, code, content, evidence, format
    evidence_type: str = ""    # url, screenshot, code, data, text


@dataclass
class Checklist:
    """Parsed checklist from a task brief."""
    task_id: str = ""
    task_title: str = ""
    criteria: list[Criterion] = field(default_factory=list)
    total_weight: float = 0.0
    acceptance_summary: str = ""
    parsed_at: float = field(default_factory=time.time)


@dataclass
class Scorecard:
    """Self-score against the checklist."""
    checklist_id: str = ""
    scores: dict[str, float] = field(default_factory=dict)  # criterion_id → 0-100
    notes: dict[str, str] = field(default_factory=dict)      # criterion_id → evidence
    total_score: float = 0.0
    weighted_score: float = 0.0
    confidence: str = "none"   # none, partial, full
    should_submit: bool = False
    threshold: float = 70.0    # minimum score to submit
    missing: list[str] = field(default_factory=list)
    scored_at: float = field(default_factory=time.time)


@dataclass
class Outcome:
    """Record of what happened after submission."""
    task_id: str = ""
    task_title: str = ""
    platform: str = ""
    reward: float = 0.0
    won: bool = False
    submitted_score: float = 0.0
    what_scored: list[str] = field(default_factory=list)
    what_missed: list[str] = field(default_factory=list)
    competition_notes: str = ""
    lesson: str = ""
    recorded_at: float = field(default_factory=time.time)


class RubricParser:
    """Parse task description into structured checklist.

    Input: raw task text (title + description)
    Output: Checklist with weighted criteria
    """

    def parse(self, task_id: str, title: str, description: str) -> Checklist:
        text = f"{title}\n\n{description}"
        criteria = []

        # Extract explicit requirements
        criteria.extend(self._extract_requirements(text))
        # Extract acceptance criteria
        criteria.extend(self._extract_acceptance(text))
        # Extract deliverables
        criteria.extend(self._extract_deliverables(text))
        # Extract constraints
        criteria.extend(self._extract_constraints(text))

        # Deduplicate
        seen = set()
        unique = []
        for c in criteria:
            key = c.description.lower()[:50]
            if key not in seen:
                seen.add(key)
                unique.append(c)

        # Assign weights
        total = sum(c.weight for c in unique) or 1.0
        for c in unique:
            c.weight = c.weight / total

        return Checklist(
            task_id=task_id,
            task_title=title,
            criteria=unique,
            total_weight=total,
            acceptance_summary=self._summarize(unique),
        )

    def _extract_requirements(self, text: str) -> list[Criterion]:
        criteria = []
        # Look for "must", "required", "shall", numbered lists
        patterns = [
            r'(?:must|shall|required?|needs? to|should)\s+(.{20,120})',
            r'(?:\d+[\.\)]\s*)(.{15,150})',
            r'(?:\-\s+)(.{15,150})',
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                desc = m.group(1).strip().rstrip('.')
                if len(desc) > 15:
                    criteria.append(Criterion(
                        id=f"req_{len(criteria)}",
                        description=desc,
                        weight=1.0,
                        verifiable=self._is_verifiable(desc),
                        category=self._categorize(desc),
                        evidence_type=self._evidence_type(desc),
                    ))
        return criteria

    def _extract_acceptance(self, text: str) -> list[Criterion]:
        criteria = []
        # Look for "acceptance", "criteria", "how winner", "judging"
        sections = re.split(r'(?:acceptance|criteria|judging|winner|selection)', text, flags=re.IGNORECASE)
        for section in sections[1:3]:  # take first 2 matches
            lines = section.split('\n')
            for line in lines[:10]:
                line = line.strip().lstrip('-*•123456789. ')
                if len(line) > 15:
                    criteria.append(Criterion(
                        id=f"acc_{len(criteria)}",
                        description=line,
                        weight=1.5,  # acceptance criteria are higher weight
                        verifiable=True,
                        category="evidence",
                        evidence_type="proof",
                    ))
        return criteria

    def _extract_deliverables(self, text: str) -> list[Criterion]:
        criteria = []
        # Look for "submit", "deliver", "provide", "include"
        patterns = [
            r'(?:submit|deliver|provide|include)\s+(.{20,150})',
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                desc = m.group(1).strip().rstrip('.')
                criteria.append(Criterion(
                    id=f"del_{len(criteria)}",
                    description=f"Deliver: {desc}",
                    weight=1.2,
                    verifiable=True,
                    category="format",
                    evidence_type="file",
                ))
        return criteria

    def _extract_constraints(self, text: str) -> list[Criterion]:
        criteria = []
        patterns = [
            r'(?:do not|never|must not|no)\s+(.{15,100})',
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                desc = m.group(1).strip().rstrip('.')
                criteria.append(Criterion(
                    id=f"con_{len(criteria)}",
                    description=f"AVOID: {desc}",
                    weight=0.8,
                    verifiable=True,
                    category="constraint",
                    evidence_type="negative",
                ))
        return criteria

    def _is_verifiable(self, desc: str) -> bool:
        indicators = ['url', 'http', 'test', 'pass', 'fail', 'check', 'verify', 'proof', 'evidence', 'screenshot']
        return any(w in desc.lower() for w in indicators)

    def _categorize(self, desc: str) -> str:
        t = desc.lower()
        if any(w in t for w in ['code', 'build', 'implement', 'fix', 'repo']):
            return 'code'
        if any(w in t for w in ['research', 'find', 'discover', 'analyze']):
            return 'research'
        if any(w in t for w in ['write', 'document', 'content', 'article']):
            return 'content'
        if any(w in t for w in ['evidence', 'proof', 'verify', 'test', 'screenshot']):
            return 'evidence'
        return 'general'

    def _evidence_type(self, desc: str) -> str:
        t = desc.lower()
        if 'url' in t or 'http' in t or 'link' in t:
            return 'url'
        if 'screenshot' in t or 'image' in t or 'visual' in t:
            return 'screenshot'
        if 'code' in t or 'repo' in t or 'file' in t:
            return 'code'
        if 'data' in t or 'csv' in t or 'json' in t:
            return 'data'
        return 'text'

    def _summarize(self, criteria: list[Criterion]) -> str:
        if not criteria:
            return "No explicit criteria found"
        verifiable = sum(1 for c in criteria if c.verifiable)
        return f"{len(criteria)} criteria, {verifiable} verifiable"


class SelfScorer:
    """Score work against checklist before submitting.

    Key principle: don't submit until score >= threshold.
    """

    def score(self, checklist: Checklist, work_artifacts: dict[str, Any]) -> Scorecard:
        card = Scorecard(checklist_id=checklist.task_id)

        for criterion in checklist.criteria:
            score, notes = self._score_criterion(criterion, work_artifacts)
            card.scores[criterion.id] = score
            card.notes[criterion.id] = notes
            if score == 0:
                card.missing.append(criterion.description)

        # Weighted score
        total_weight = sum(c.weight for c in checklist.criteria) or 1.0
        card.weighted_score = sum(
            card.scores.get(c.id, 0) * c.weight
            for c in checklist.criteria
        ) / total_weight

        card.total_score = sum(card.scores.values()) / max(1, len(card.scores))
        card.confidence = "full" if len(card.scores) == len(checklist.criteria) else "partial"
        card.should_submit = card.weighted_score >= card.threshold and not card.missing

        return card

    def _score_criterion(self, criterion: Criterion, artifacts: dict) -> tuple[float, str]:
        """Score one criterion based on available artifacts."""
        desc = criterion.description.lower()
        text_content = artifacts.get("content", "").lower()
        files = artifacts.get("files", [])
        urls = artifacts.get("urls", [])

        # Check if criterion is addressed at all
        keywords = desc.split()[:5]
        addressed = any(kw in text_content for kw in keywords if len(kw) > 3)

        if not addressed:
            return 0, f"Not addressed in submission"

        # Score based on evidence quality
        score = 50  # base for being addressed

        # Bonus for verifiable evidence
        if criterion.verifiable:
            if criterion.evidence_type == "url" and urls:
                score += 30
            elif criterion.evidence_type == "code" and files:
                score += 30
            elif criterion.evidence_type == "screenshot":
                score += 20  # harder to verify in text
            elif criterion.evidence_type == "data":
                score += 25
            else:
                score += 10

        # Bonus for detail level
        if len(text_content) > 1000:
            score += 10
        if len(text_content) > 5000:
            score += 10

        return min(100, score), f"Addressed with {'evidence' if score > 70 else 'basic coverage'}"

    def should_submit(self, card: Scorecard) -> tuple[bool, str]:
        """Determine if we should submit."""
        if card.weighted_score >= card.threshold and not card.missing:
            return True, f"Score {card.weighted_score:.0f}% exceeds threshold {card.threshold:.0f}%"
        if card.missing:
            return False, f"Missing {len(card.missing)} criteria: {'; '.join(card.missing[:3])}"
        return False, f"Score {card.weighted_score:.0f}% below threshold {card.threshold:.0f}%"


class StrategyMemory:
    """Records outcomes and learns what wins.

    After each task (win or lose), record:
    - What scored well
    - What was missed
    - What competition did differently
    - Lesson learned
    """

    def record_outcome(self, outcome: Outcome) -> None:
        _append(OUTCOMES_DB, {
            "task_id": outcome.task_id,
            "task_title": outcome.task_title,
            "platform": outcome.platform,
            "reward": outcome.reward,
            "won": outcome.won,
            "submitted_score": outcome.submitted_score,
            "what_scored": outcome.what_scored,
            "what_missed": outcome.what_missed,
            "competition_notes": outcome.competition_notes,
            "lesson": outcome.lesson,
            "recorded_at": outcome.recorded_at,
        })

    def get_lessons(self, category: str = "", platform: str = "") -> list[dict]:
        """Get relevant lessons from past outcomes."""
        outcomes = _load_outcomes()
        lessons = []
        for o in outcomes:
            if category and category not in o.get("task_title", "").lower():
                continue
            if platform and o.get("platform") != platform:
                continue
            if o.get("lesson"):
                lessons.append({
                    "task": o.get("task_title", ""),
                    "won": o.get("won", False),
                    "lesson": o["lesson"],
                    "what_scored": o.get("what_scored", []),
                    "what_missed": o.get("what_missed", []),
                })
        return lessons

    def get_win_rate(self) -> float:
        outcomes = _load_outcomes()
        if not outcomes:
            return 0.0
        wins = sum(1 for o in outcomes if o.get("won"))
        return wins / len(outcomes)

    def get_top_lessons(self, n: int = 5) -> list[str]:
        """Get most common lessons from wins."""
        outcomes = _load_outcomes()
        win_lessons = []
        for o in outcomes:
            if o.get("won") and o.get("lesson"):
                win_lessons.append(o["lesson"])
        # Deduplicate and return top N
        seen = set()
        unique = []
        for l in win_lessons:
            if l not in seen:
                seen.add(l)
                unique.append(l)
        return unique[:n]

    def summary(self) -> dict:
        outcomes = _load_outcomes()
        return {
            "total_tasks": len(outcomes),
            "wins": sum(1 for o in outcomes if o.get("won")),
            "win_rate": self.get_win_rate(),
            "total_earned": sum(o.get("reward", 0) for o in outcomes if o.get("won")),
            "top_lessons": self.get_top_lessons(),
        }


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _load_outcomes() -> list[dict]:
    if not OUTCOMES_DB.exists():
        return []
    outcomes = []
    for line in OUTCOMES_DB.read_text().splitlines():
        if line.strip():
            try:
                outcomes.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return outcomes
