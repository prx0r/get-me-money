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


# === Postmortem: why did you lose? ===

class Postmortem:
    """Analyze a submission failure and extract actionable lessons."""

    def analyze(self, our_scorecard: Scorecard, winner_artifact: dict | None = None,
                competition_size: int = 0, outcome_notes: str = "") -> dict:
        """Compare our work to what won (if visible) and extract lessons."""

        analysis = {
            "our_score": our_scorecard.weighted_score,
            "our_gaps": [],
            "winner_comparison": None,
            "lessons": [],
            "should_retry_class": True,
            "procedure_candidate": None,
        }

        # Find our weak criteria
        for criterion_id, score in our_scorecard.scores.items():
            if score < 60:
                note = our_scorecard.notes.get(criterion_id, "")
                analysis["our_gaps"].append({
                    "criterion": criterion_id,
                    "score": score,
                    "note": note,
                })

        # Compare to winner if available
        if winner_artifact:
            analysis["winner_comparison"] = self._compare_to_winner(
                our_scorecard, winner_artifact
            )

        # Generate lessons
        analysis["lessons"] = self._extract_lessons(analysis)

        # Should we ever try this task class again?
        if our_scorecard.weighted_score < 40 and competition_size > 20:
            analysis["should_retry_class"] = False

        # Candidate for reusable procedure
        if our_scorecard.weighted_score >= 60:
            analysis["procedure_candidate"] = self._extract_procedure(our_scorecard)

        return analysis

    def _compare_to_winner(self, ours: Scorecard, winner: dict) -> dict:
        """What did the winner do differently?"""
        comparison = {
            "winner_score": winner.get("score", 0),
            "score_delta": winner.get("score", 0) - ours.weighted_score,
            "winner_approach": winner.get("approach", ""),
            "what_they_had_we_didnt": [],
            "what_we_had_they_didnt": [],
        }

        # Compare criterion-level scores
        winner_scores = winner.get("criteria_scores", {})
        for cid, our_score in ours.scores.items():
            winner_score = winner_scores.get(cid, 0)
            if winner_score > our_score + 15:
                comparison["what_they_had_we_didnt"].append({
                    "criterion": cid,
                    "their_score": winner_score,
                    "our_score": our_score,
                    "gap": winner_score - our_score,
                })
            elif our_score > winner_score + 15:
                comparison["what_we_had_they_didnt"].append({
                    "criterion": cid,
                    "our_score": our_score,
                    "their_score": winner_score,
                })

        return comparison

    def _extract_lessons(self, analysis: dict) -> list[str]:
        """Turn analysis into actionable lessons."""
        lessons = []

        # From gaps
        for gap in analysis["our_gaps"]:
            if gap["score"] < 40:
                lessons.append(f"Critical gap: {gap['criterion']} scored {gap['score']}/100")
            elif gap["score"] < 60:
                lessons.append(f"Weak area: {gap['criterion']} needs improvement")

        # From winner comparison
        wc = analysis.get("winner_comparison")
        if wc:
            for item in wc.get("what_they_had_we_didnt", []):
                lessons.append(f"Winner had: {item['criterion']} (their {item['their_score']} vs our {item['our_score']})")
            if wc.get("winner_approach"):
                lessons.append(f"Winner approach: {wc['winner_approach'][:200]}")

        return lessons[:5]  # Top 5 lessons

    def _extract_procedure(self, scorecard: Scorecard) -> dict:
        """Extract a reusable procedure from successful patterns."""
        strong = [(cid, s) for cid, s in scorecard.scores.items() if s >= 70]
        return {
            "what_worked": [cid for cid, _ in strong],
            "strength_score": sum(s for _, s in strong) / max(1, len(strong)),
            "reusable_steps": [scorecard.notes.get(cid, "") for cid, _ in strong if scorecard.notes.get(cid)],
        }


# === CompetitionAnalyzer: understand the field ===

class CompetitionAnalyzer:
    """Analyze competition to inform strategy."""

    def analyze(self, task: dict, our_history: list[dict] | None = None) -> dict:
        """Analyze competition for a task."""
        subs = task.get("submission_count", task.get("competition_estimate", 0))

        analysis = {
            "field_size": subs,
            "difficulty": self._difficulty_tier(subs),
            "strategy_recommendation": "",
            "estimated_win_probability": 0.0,
            "skip_reason": None,
        }

        if subs > 50:
            analysis["difficulty"] = "extreme"
            analysis["strategy_recommendation"] = "skip unless exceptional at this category"
            analysis["skip_reason"] = f"{subs} competitors — negative EV unless top 5%"
            analysis["estimated_win_probability"] = 0.02
        elif subs > 30:
            analysis["difficulty"] = "hard"
            analysis["strategy_recommendation"] = "only if strong track record in this category"
            analysis["estimated_win_probability"] = 0.05
        elif subs > 15:
            analysis["difficulty"] = "moderate"
            analysis["strategy_recommendation"] = "good opportunity if well-prepared"
            analysis["estimated_win_probability"] = 0.10
        elif subs > 5:
            analysis["difficulty"] = "easy"
            analysis["strategy_recommendation"] = "strong opportunity"
            analysis["estimated_win_probability"] = 0.20
        else:
            analysis["difficulty"] = "open"
            analysis["strategy_recommendation"] = "excellent — few competitors"
            analysis["estimated_win_probability"] = 0.40

        # Adjust based on our history
        if our_history:
            avg_score = sum(h.get("score", 0) for h in our_history) / len(our_history)
            if avg_score > 80:
                analysis["estimated_win_probability"] *= 1.5
                analysis["strategy_recommendation"] += " (strong track record)"
            elif avg_score < 50:
                analysis["estimated_win_probability"] *= 0.5
                analysis["strategy_recommendation"] += " (weak track record)"

        return analysis

    def _difficulty_tier(self, subs: int) -> str:
        if subs > 50: return "extreme"
        if subs > 30: return "hard"
        if subs > 15: return "moderate"
        if subs > 5: return "easy"
        return "open"


# === ProcedureExtractor: turn experience into playbooks ===

PROCEDURES_DB = DATA_DIR / "repute-procedures.jsonl"


class ProcedureExtractor:
    """Extract reusable procedures from repeated success patterns."""

    def __init__(self):
        self.min_attempts = 3
        self.min_success_rate = 0.5

    def extract(self, category: str, outcomes: list[dict]) -> dict | None:
        """Check if we have enough data to extract a procedure."""
        cat_outcomes = [o for o in outcomes if category in o.get("task_title", "").lower()]

        if len(cat_outcomes) < self.min_attempts:
            return None

        wins = [o for o in cat_outcomes if o.get("won")]
        win_rate = len(wins) / len(cat_outcomes)

        if win_rate < self.min_success_rate:
            return None

        # Extract common patterns from wins
        all_scored = []
        all_missed = []
        for o in wins:
            all_scored.extend(o.get("what_scored", []))
            all_missed.extend(o.get("what_missed", []))

        # Most common successes
        scored_freq = {}
        for s in all_scored:
            scored_freq[s] = scored_freq.get(s, 0) + 1
        top_scored = sorted(scored_freq.items(), key=lambda x: x[1], reverse=True)[:5]

        # Most common failures (things to avoid)
        missed_freq = {}
        for m in all_missed:
            missed_freq[m] = missed_freq.get(m, 0) + 1
        top_missed = sorted(missed_freq.items(), key=lambda x: x[1], reverse=True)[:3]

        procedure = {
            "category": category,
            "attempts": len(cat_outcomes),
            "wins": len(wins),
            "win_rate": round(win_rate, 2),
            "core_steps": [s[0] for s in top_scored],
            "avoid": [m[0] for m in top_missed],
            "avg_reward": sum(o.get("reward", 0) for o in wins) / max(1, len(wins)),
            "created_at": time.time(),
        }

        # Save
        _append(PROCEDURES_DB, procedure)
        return procedure

    def get_procedure(self, category: str) -> dict | None:
        """Get the best procedure for a category."""
        if not PROCEDURES_DB.exists():
            return None
        best = None
        for line in PROCEDURES_DB.read_text().splitlines():
            if not line.strip():
                continue
            try:
                p = json.loads(line)
                if p.get("category") == category:
                    if best is None or p.get("win_rate", 0) > best.get("win_rate", 0):
                        best = p
            except json.JSONDecodeError:
                continue
        return best

    def all_procedures(self) -> list[dict]:
        if not PROCEDURES_DB.exists():
            return []
        procs = []
        seen = set()
        for line in PROCEDURES_DB.read_text().splitlines():
            if not line.strip():
                continue
            try:
                p = json.loads(line)
                key = p.get("category", "")
                if key not in seen:
                    seen.add(key)
                    procs.append(p)
            except json.JSONDecodeError:
                continue
        return sorted(procs, key=lambda x: x.get("win_rate", 0), reverse=True)


# === TaskPipeline: the complete flow ===

class TaskPipeline:
    """Complete task flow: parse → check → build → score → submit → learn.

    This is the main entry point that wires everything together.
    """

    def __init__(self):
        self.parser = RubricParser()
        self.scorer = SelfScorer()
        self.memory = StrategyMemory()
        self.competition = CompetitionAnalyzer()
        self.postmortem = Postmortem()
        self.procedures = ProcedureExtractor()

    def start_task(self, task_id: str, title: str, description: str,
                   submission_count: int = 0) -> dict:
        """Step 1: Parse task and decide whether to attempt."""

        # Parse rubric
        checklist = self.parser.parse(task_id, title, description)

        # Analyze competition
        comp = self.competition.analyze({
            "submission_count": submission_count,
        })

        # Check if we have a procedure for this category
        category = self._detect_category(title, description)
        procedure = self.procedures.get_procedure(category)

        # Prior lessons
        lessons = self.memory.get_lessons(category=category)

        decision = {
            "task_id": task_id,
            "title": title,
            "category": category,
            "checklist": checklist,
            "competition": comp,
            "procedure": procedure,
            "prior_lessons": lessons,
            "should_attempt": comp.get("estimated_win_probability", 0) > 0.05,
            "reason": comp.get("strategy_recommendation", ""),
        }

        if not decision["should_attempt"]:
            decision["reason"] = f"Skip: {comp.get('skip_reason', 'low EV')}"

        return decision

    def score_submission(self, checklist: Checklist, artifacts: dict) -> Scorecard:
        """Step 2: Score our work before submitting."""
        return self.scorer.score(checklist, artifacts)

    def should_submit(self, scorecard: Scorecard) -> tuple[bool, str]:
        """Step 3: Final gate — submit or revise?"""
        return self.scorer.should_submit(scorecard)

    def record_outcome(self, task_id: str, title: str, platform: str,
                       reward: float, won: bool, scorecard: Scorecard,
                       winner_artifact: dict | None = None,
                       competition_size: int = 0) -> dict:
        """Step 4: Record outcome and extract lessons."""

        # Run postmortem
        analysis = self.postmortem.analyze(
            scorecard, winner_artifact, competition_size
        )

        # Record in memory
        outcome = Outcome(
            task_id=task_id,
            task_title=title,
            platform=platform,
            reward=reward,
            won=won,
            submitted_score=scorecard.weighted_score,
            what_scored=[f"{cid}: {score}" for cid, score in scorecard.scores.items() if score >= 70],
            what_missed=[g["criterion"] for g in analysis["our_gaps"]],
            lesson="; ".join(analysis["lessons"][:2]),
        )
        self.memory.record_outcome(outcome)

        # Check if we can extract a procedure
        cat = self._detect_category(title, "")
        outcomes = self.memory.get_lessons()
        procedure = self.procedures.extract(cat, [
            {"task_title": title, "won": won, "reward": reward,
             "what_scored": outcome.what_scored, "what_missed": outcome.what_missed}
        ])

        return {
            "outcome": "won" if won else "lost",
            "score": scorecard.weighted_score,
            "analysis": analysis,
            "procedure_extracted": procedure is not None,
        }

    def _detect_category(self, title: str, desc: str) -> str:
        t = (title + " " + desc).lower()
        if any(w in t for w in ["code", "build", "implement", "fix", "repo"]):
            return "code"
        if any(w in t for w in ["research", "find", "discover", "analyze", "investigate"]):
            return "research"
        if any(w in t for w in ["write", "content", "article", "blog"]):
            return "content"
        if any(w in t for w in ["design", "ui", "ux", "visual"]):
            return "design"
        if any(w in t for w in ["data", "dataset", "csv", "extract"]):
            return "data"
        if any(w in t for w in ["api", "integration", "automation"]):
            return "api"
        return "general"
