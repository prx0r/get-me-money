"""Opportunity evaluator — EV scoring, cost estimation, go/no-go."""

from __future__ import annotations

import logging
from typing import Optional

from get_me_money.config import Config
from get_me_money.models import (
    Evaluation, Opportunity, Platform, TaskCategory,
)

log = logging.getLogger(__name__)

# Base cost rates (USD per unit)
COST_PER_1K_TOKENS = 0.003       # approximate inference cost
COST_PER_HTTP_REQ = 0.0002       # approximate API call
COST_PER_BOUNTY_FEE = 0.10       # 10% typical marketplace fee

# Category difficulty weights (hours, rough estimates)
CATEGORY_HOURS = {
    TaskCategory.RESEARCH: 1.5,
    TaskCategory.DATA_EXTRACTION: 1.0,
    TaskCategory.CODE_FIX: 3.0,
    TaskCategory.CODE_FEATURE: 5.0,
    TaskCategory.CONTENT: 2.0,
    TaskCategory.DOCUMENTATION: 1.5,
    TaskCategory.API_WORK: 2.5,
    TaskCategory.TESTING: 2.0,
    TaskCategory.DESIGN: 3.0,
    TaskCategory.UNKNOWN: 2.0,
}

# Platform fee percentages
PLATFORM_FEES = {
    Platform.BOUNTY: 0.10,
    Platform.ALGORA: 0.0,      # paid via PR merge, no platform fee
    Platform.OPIRE: 0.0,
    Platform.CLUSTLY: 0.04,
    Platform.SUPERTEAM: 0.0,
    Platform.TASKMARKET: 0.075,  # 7.5% USDC fee
    Platform.AGENTHANSA: 0.0,    # affiliate model, not task fee
    Platform.OLAS: 0.0,
    Platform.VIRTUALS: 0.0,
}


class Evaluator:
    """Decides which opportunities are worth attempting."""

    def __init__(self, config: Config):
        self.config = config

    def evaluate(self, opp: Opportunity) -> Evaluation:
        ev = Evaluation(opportunity_id=opp.id)

        # Estimate cost
        hours = CATEGORY_HOURS.get(opp.category, 2.0)
        token_cost = hours * (15_000 / 1000) * COST_PER_1K_TOKENS  # ~15k tokens/hr of work
        api_cost = hours * 5 * COST_PER_HTTP_REQ           # ~5 API calls/hr
        fee_pct = PLATFORM_FEES.get(opp.platform, 0.10)
        fee = opp.reward * fee_pct
        ev.estimated_cost = token_cost + api_cost + fee
        ev.estimated_hours = hours

        # Estimate probability of success
        p = self._estimate_p_success(opp)
        ev.competition_score = self._competition_score(opp)

        # Learning value — how reusable is this skill?
        ev.ev_learning = self._learning_value(opp)
        ev.ev_reusable = self._reusable_asset_value(opp)

        # Compute EV
        ev.compute_ev(reward=opp.reward, p_success=p, cost=ev.estimated_cost)

        # Final gate checks
        budget = self.config.budget
        if opp.reward < budget.min_reward:
            ev.should_attempt = False
            ev.reasoning = f"Reward ${opp.reward:.2f} < min ${budget.min_reward:.2f}"
        elif ev.ev_total < budget.min_ev:
            ev.should_attempt = False
            ev.reasoning = f"EV ${ev.ev_total:.2f} < min ${budget.min_ev:.2f}"
        elif ev.estimated_cost > budget.per_attempt_cap:
            ev.should_attempt = False
            ev.reasoning = f"Cost ${ev.estimated_cost:.2f} > cap ${budget.per_attempt_cap:.2f}"
        elif p < 0.10:
            ev.should_attempt = False
            ev.reasoning = f"P(success) {p:.0%} < 10%"
        else:
            ev.reasoning = (
                f"EV=${ev.ev_total:.2f} P={p:.0%} cost=${ev.estimated_cost:.2f} "
                f"reward=${opp.reward:.2f}"
            )

        return ev

    def _estimate_p_success(self, opp: Opportunity) -> float:
        """Estimate probability of successful completion + payout."""
        base = 0.35  # base rate

        # Platform reliability adjustment
        base *= opp.payment_reliability

        # Category difficulty adjustment
        hours = CATEGORY_HOURS.get(opp.category, 2.0)
        if hours <= 1.5:
            base *= 1.2   # simpler tasks, higher success
        elif hours >= 4.0:
            base *= 0.7   # complex tasks, lower success

        # Competition adjustment
        if opp.competition_estimate > 20:
            base *= 0.6
        elif opp.competition_estimate > 10:
            base *= 0.8

        # Verification strength — easier to verify = easier to get paid
        base *= (0.7 + 0.3 * opp.verification_strength)

        # Reward amount — bigger rewards attract more competition
        if opp.reward > 500:
            base *= 0.8
        elif opp.reward > 100:
            base *= 0.9

        return max(0.05, min(0.95, base))

    def _competition_score(self, opp: Opportunity) -> float:
        c = opp.competition_estimate
        if c == 0:
            return 0.1
        if c <= 5:
            return 0.3
        if c <= 15:
            return 0.5
        if c <= 30:
            return 0.7
        return 0.9

    def _learning_value(self, opp: Opportunity) -> float:
        """How much does attempting this teach us? 0-1 scale."""
        score = 0.0
        # Research/data extraction builds reusable skills
        if opp.category in (TaskCategory.RESEARCH, TaskCategory.DATA_EXTRACTION):
            score += 0.3
        # Code work builds reusable patterns
        if opp.category in (TaskCategory.CODE_FIX, TaskCategory.CODE_FEATURE):
            score += 0.2
        # API work is directly reusable
        if opp.category == TaskCategory.API_WORK:
            score += 0.4
        # New platform = learning
        if opp.platform not in (Platform.BOUNTY, Platform.ALGORA):
            score += 0.1
        return min(1.0, score)

    def _reusable_asset_value(self, opp: Opportunity) -> float:
        """Could the output of this task become a paid service?"""
        if opp.category == TaskCategory.API_WORK:
            return 0.5
        if opp.category == TaskCategory.DATA_EXTRACTION:
            return 0.4
        if opp.category == TaskCategory.RESEARCH:
            return 0.3
        if opp.category in (TaskCategory.CODE_FIX, TaskCategory.CODE_FEATURE):
            return 0.2
        return 0.1

    def rank(self, evaluations: list[tuple[Opportunity, Evaluation]]) -> list[tuple[Opportunity, Evaluation]]:
        """Sort by EV total, descending."""
        return sorted(evaluations, key=lambda x: x[1].ev_total, reverse=True)
