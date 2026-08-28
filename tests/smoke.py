"""Offline core smoke test. Run: GMM_DATA_DIR=$(mktemp -d) python tests/smoke.py"""
import os, tempfile
os.environ.setdefault("GMM_DATA_DIR", tempfile.mkdtemp(prefix="gmm-test-"))

from get_me_money.config import Config
from get_me_money.evaluator import Evaluator
from get_me_money.ledger import load_attempts, load_opportunities, save_attempt, save_opportunity
from get_me_money.models import Attempt, Opportunity, Outcome, Platform, TaskCategory

c=Config(); c.load()
o=Opportunity(platform=Platform.TASKMARKET, external_id="0xabc", title="Research test", description="research a thing", reward=3, currency="USDC", category=TaskCategory.RESEARCH, competition_estimate=20, verification_strength=.8, payment_reliability=.85, raw={"execution_supported":True})
save_opportunity(o)
assert load_opportunities()[0].platform is Platform.TASKMARKET
assert load_opportunities()[0].category is TaskCategory.RESEARCH

ev=Evaluator(c).evaluate(o)
assert ev.estimated_cost < 0.25, ev.estimated_cost

a=Attempt(opportunity_id=o.id, platform=Platform.TASKMARKET, external_id=o.external_id, title=o.title, outcome=Outcome.PENDING, cost=.01, metadata={"category":"research"})
save_attempt(a)
a.finalize(Outcome.SUCCEEDED, reward=1.85, fees=.15); save_attempt(a)
rows=load_attempts(); assert len(rows)==1; assert rows[0].outcome is Outcome.SUCCEEDED; assert rows[0].metadata["category"]=="research"
print("smoke ok", {"ev":ev.ev_cash,"net":rows[0].net})
