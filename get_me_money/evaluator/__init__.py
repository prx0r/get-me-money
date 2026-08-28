"""Cash-EV evaluator. Learning is used to calibrate probabilities, not invented dollars."""
from __future__ import annotations

import time
from get_me_money.config import Config
from get_me_money.memory import Memory
from get_me_money.models import Evaluation, Opportunity, Platform, TaskCategory

COST_PER_1K_TOKENS = 0.003
TOKENS_PER_HOUR = 15_000
HTTP_COST_PER_HOUR = 0.001
CATEGORY_HOURS = {
    TaskCategory.RESEARCH: 0.75,
    TaskCategory.DATA_EXTRACTION: 0.75,
    TaskCategory.CODE_FIX: 2.0,
    TaskCategory.CODE_FEATURE: 3.0,
    TaskCategory.CONTENT: 1.0,
    TaskCategory.DOCUMENTATION: 1.0,
    TaskCategory.API_WORK: 1.5,
    TaskCategory.TESTING: 1.5,
    TaskCategory.DESIGN: 2.0,
    TaskCategory.UNKNOWN: 1.5,
}
PLATFORM_FEES = {Platform.TASKMARKET: 0.075, Platform.SUPERTEAM: 0.0, Platform.BOUNTY: 0.10}


class Evaluator:
    def __init__(self, config: Config):
        self.config = config
        self.memory = Memory()

    def evaluate(self, opp: Opportunity) -> Evaluation:
        ev = Evaluation(opportunity_id=opp.id)
        hours = CATEGORY_HOURS.get(opp.category, 1.5)
        ev.estimated_hours = hours
        ev.estimated_cost = (hours * TOKENS_PER_HOUR / 1000.0 * COST_PER_1K_TOKENS) + (hours * HTTP_COST_PER_HOUR)
        ev.platform_fee_rate = PLATFORM_FEES.get(opp.platform, 0.0)
        ev.competition_score = self._competition_score(opp.competition_estimate)

        prior = self._prior_probability(opp)
        p = self.memory.calibrated_probability(opp.category.value, opp.platform.value, prior)
        ev.probability_of_success = p
        ev.ev_cash = p * opp.reward * (1.0 - ev.platform_fee_rate) - ev.estimated_cost
        ev.learning_score = self._learning_score(opp)
        ev.reusable_score = self._reusable_score(opp)
        # Cash EV dominates; learning only breaks ties rather than pretending to be USD.
        ev.rank_score = ev.ev_cash + 0.02 * ev.learning_score + 0.02 * ev.reusable_score

        b = self.config.budget
        if opp.expires_at and opp.expires_at <= time.time():
            ev.reasoning = "expired"
        elif not opp.raw.get("execution_supported", True):
            ev.reasoning = str(opp.raw.get("execution_block_reason", "platform flow not safely automatable"))
        elif opp.currency.upper() not in {"USD", "USDC"}:
            ev.reasoning = f"unsupported currency {opp.currency}"
        elif opp.reward < b.min_reward:
            ev.reasoning = f"reward ${opp.reward:.2f} below minimum ${b.min_reward:.2f}"
        elif ev.estimated_cost > b.per_attempt_cap:
            ev.reasoning = f"estimated cost ${ev.estimated_cost:.3f} exceeds per-attempt cap ${b.per_attempt_cap:.2f}"
        elif p < b.min_success_probability:
            ev.reasoning = f"estimated success probability {p:.1%} below floor {b.min_success_probability:.1%}"
        elif ev.ev_cash < b.min_ev:
            ev.reasoning = f"cash EV ${ev.ev_cash:.3f} below minimum ${b.min_ev:.2f}"
        else:
            ev.should_attempt = True
            ev.reasoning = f"cashEV=${ev.ev_cash:.3f} p={p:.1%} estCost=${ev.estimated_cost:.3f} reward=${opp.reward:.2f}"
        return ev

    def rank(self, rows):
        return sorted(rows, key=lambda x: x[1].rank_score, reverse=True)

    def _prior_probability(self, opp: Opportunity) -> float:
        p = 0.30 * max(0.25, min(1.0, opp.payment_reliability))
        if opp.category in {TaskCategory.RESEARCH, TaskCategory.DATA_EXTRACTION, TaskCategory.DOCUMENTATION}:
            p *= 1.25
        if opp.category in {TaskCategory.CODE_FEATURE, TaskCategory.DESIGN}:
            p *= 0.75
        # TryBounty has proven demand for research/data — boost those tasks
        if opp.platform == Platform.BOUNTY and opp.category in {TaskCategory.RESEARCH, TaskCategory.DATA_EXTRACTION}:
            p *= 1.15
        if opp.competition_estimate >= 30:
            p *= 0.40
        elif opp.competition_estimate >= 15:
            p *= 0.60
        elif opp.competition_estimate >= 5:
            p *= 0.80
        p *= 0.7 + 0.3 * max(0, min(1, opp.verification_strength))
        return max(0.03, min(0.70, p))

    @staticmethod
    def _competition_score(n: int) -> float:
        return min(1.0, max(0.0, n / 40.0))

    @staticmethod
    def _learning_score(opp: Opportunity) -> float:
        return 1.0 if opp.category in {TaskCategory.RESEARCH, TaskCategory.CODE_FIX, TaskCategory.API_WORK} else 0.4

    @staticmethod
    def _reusable_score(opp: Opportunity) -> float:
        return 1.0 if opp.category in {TaskCategory.API_WORK, TaskCategory.DATA_EXTRACTION} else 0.3
