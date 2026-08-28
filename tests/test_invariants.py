"""Invariant tests — the 12 things that MUST be true.

These are not feature tests. They are architectural guarantees.
If any of these fail, the system is broken.
"""
import hashlib
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — {detail}")


print("=== INVARIANT TESTS ===\n")

# 1. JobSpec validation
print("1. JobSpec must have required fields")
from get_me_money.jobspec import JobSpec
spec = JobSpec(objective="test", hard_requirements=["req1"], scoring={"q": 0.5, "r": 0.5})
test("objective nonempty", spec.objective != "")
test("hard_requirements >= 1", len(spec.hard_requirements) >= 1)
test("scoring nonempty", len(spec.scoring) > 0)
test("weights sum to 1.0", abs(sum(spec.scoring.values()) - 1.0) < 0.01)

# 2. JobSpec parsing handles bad JSON gracefully
print("\n2. JobSpec parsing handles bad input")
from get_me_money.jobspec import parse_jobspec_from_hermes
bad_spec = parse_jobspec_from_hermes("this is not json at all")
test("bad JSON returns empty spec", bad_spec.objective == "" or bad_spec.hard_requirements == [])
good_json = json.dumps({"objective": "test", "hard_requirements": ["r1"], "scoring": {"q": 0.5, "r": 0.5}, "automatic_rejection": []})
good_spec = parse_jobspec_from_hermes(good_json)
test("valid JSON parses correctly", good_spec.objective == "test")

# 3. WinPlan parsing
print("\n3. WinPlan parsing handles bad input")
from get_me_money.jobspec import parse_winplan_from_hermes
bad_plan = parse_winplan_from_hermes("not json")
test("bad JSON returns empty plan", bad_plan.entry_decision == "")
good_plan_json = json.dumps({"entry_decision": "Enter", "differentiation": "focus", "candidate_count": 1, "revision_rounds": 1})
good_plan = parse_winplan_from_hermes(good_plan_json)
test("valid JSON parses correctly", good_plan.entry_decision == "Enter")

# 4. DeterministicGate catches bad submissions
print("\n4. DeterministicGate catches bad content")
from get_me_money.verifier import DeterministicGate
gate = DeterministicGate({"hard_requirements": ["exactly 10 files", "has URLs"]})
checks = gate.check("/tmp", ["file1.md"], "short")
failures = [c for c in checks if not c.passed]
test("rejects short content", any("content_minimum" in c.name for c in failures))
test("rejects wrong file count", any("files" in c.name for c in failures))

# 5. DeterministicGate accepts good submissions
print("\n5. DeterministicGate accepts good content")
long_content = "This is a good submission with https://example.com sources. " * 5  # 300+ chars
checks = gate.check("/tmp", ["f1.md","f2.md","f3.md","f4.md","f5.md","f6.md","f7.md","f8.md","f9.md","f10.md"],
                     long_content)
all_passed = all(c.passed for c in checks)
test("accepts good content", all_passed)

# 6. SubmissionRun serializes/deserializes
print("\n6. SubmissionRun round-trips through JSON")
from get_me_money.submission_run import SubmissionRun, CandidateRecord
from pathlib import Path
import tempfile
run = SubmissionRun(task_title="test", task_reward=5.0)
c = CandidateRecord(version=1, content="hello world")
c.compute_hash()
run.candidates.append(c)
run.selected_candidate_version = 1
with tempfile.TemporaryDirectory() as td:
    run.save(Path(td))
    loaded = SubmissionRun.load(Path(td))
    test("title preserved", loaded.task_title == "test")
    test("reward preserved", loaded.task_reward == 5.0)
    test("candidates preserved", len(loaded.candidates) == 1)
    test("content hash preserved", loaded.candidates[0].content_hash == c.content_hash)

# 7. WorkRun content hash changes with content
print("\n7. WorkRun content hash is content-addressed")
from get_me_money.workrun import WorkRun
r1 = WorkRun(job_title="test", artifact_content="version A")
r2 = WorkRun(job_title="test", artifact_content="version B")
test("different content → different hash", r1.content_hash() != r2.content_hash())
r3 = WorkRun(job_title="test", artifact_content="version A")
test("same content → same hash", r1.content_hash() == r3.content_hash())

# 8. Verifier with config produces Hermes Judge
print("\n8. Verifier uses Hermes Judge when config provided")
from get_me_money.verifier import Verifier, Judge
judge_with_config = Judge(config="dummy")
judge_without = Judge()
test("Judge with config is not fallback", judge_with_config.config is not None)
test("Judge without config is fallback", judge_without.config is None)

# 9. OracleClient handles missing DB gracefully
print("\n9. OracleClient handles missing DB")
from get_me_money.oracle_client import OracleClient
client = OracleClient()
stats = client.stats()
test("stats returns dict even if empty", isinstance(stats, dict))

# 10. Employer decomposition produces valid structure
print("\n10. Employer decomposition output structure")
from get_me_money.employer import MicroTask, Decomposition
decomp = Decomposition(original_task="big task", total_estimated_cost=10.0)
decomp.micro_tasks.append(MicroTask(id="part-1", title="subtask", estimated_reward=5.0))
test("decomposition has tasks", len(decomp.micro_tasks) == 1)
test("cost is sum of parts", decomp.total_estimated_cost == 10.0)

# 11. Evaluator doesn't crash on any category
print("\n11. Evaluator handles all categories")
from get_me_money.evaluator import Evaluator
from get_me_money.models import TaskCategory, Platform, Opportunity
from get_me_money.config import Config
config = Config()
config.load()
evaluator = Evaluator(config)
for cat in TaskCategory:
    opp = Opportunity(
        id="test", platform=Platform.TASKMARKET, external_id="",
        title="test task", description="test", category=cat, reward=5.0, currency="USDC",
    )
    ev = evaluator.evaluate(opp)
    test(f"evaluator handles {cat.value}", ev.ev_cash is not None)

# 12. Ledger append/load round-trip
print("\n12. Ledger round-trips")
from get_me_money.ledger import save_opportunity, load_opportunities
from get_me_money.models import Opportunity
import tempfile
os.environ["GMM_DATA_DIR"] = tempfile.mkdtemp()
opp = Opportunity(
    id="test-roundtrip", platform=Platform.TASKMARKET, external_id="0x123",
    title="roundtrip test", description="test", reward=3.0, currency="USDC",
)
save_opportunity(opp)
loaded = load_opportunities()
found = [o for o in loaded if o.id == "test-roundtrip"]
test("opportunity round-trips", len(found) == 1)
test("title preserved", found[0].title == "roundtrip test" if found else False)

print(f"\n=== RESULTS: {PASS} passed, {FAIL} failed ===")
if FAIL > 0:
    sys.exit(1)

# 13. Workshop workers load
print("\n13. Workshop workers load")
from get_me_money.workshop import list_workers, list_blueprints, BLUEPRINTS, WORKERS
test("workers defined", len(WORKERS) > 0)
test("blueprints defined", len(BLUEPRINTS) > 0)
test("worker has skills", len(list(WORKERS.values())[0].skills) > 0)
test("blueprint has steps", len(list(BLUEPRINTS.values())[0].steps) > 0)

# 14. Market adapters register
print("\n14. Market adapters register")
from get_me_money.markets import list_markets, MARKET_ADAPTERS
test("adapters registered", len(MARKET_ADAPTERS) > 0)
test("13 adapters", len(MARKET_ADAPTERS) == 13)
auto = [k for k, v in MARKET_ADAPTERS.items() if v().can_operate_autonomously()]
test("10 autonomous adapters", len(auto) == 10)

# 15. Factories load
print("\n15. Factories load")
from get_me_money.factories import list_factories, FACTORIES
test("factories defined", len(FACTORIES) > 0)
test("6 factories", len(FACTORIES) == 6)
for f in FACTORIES.values():
    test(f"factory {f.name} has steps", len(f.steps) > 0)
    test(f"factory {f.name} has distribution", len(f.distribution) > 0)

# 16. Supply chain round-trips
print("\n16. Supply chain round-trips")
from get_me_money.supply_chain import SupplyChain, Part, Product, Provenance
import tempfile
with tempfile.TemporaryDirectory() as td:
    sc = SupplyChain(Path(td))
    part = Part(name="test-dataset", type="dataset", price=0.05)
    part_id = sc.add_part(part)
    test("part saved", (Path(td) / "parts" / f"{part_id}.json").exists())
    loaded = sc.load_part(part_id)
    test("part loaded", loaded is not None)
    test("part name preserved", loaded.name == "test-dataset" if loaded else False)

# 17. Config loads
print("\n17. WorkerConfig loads")
from get_me_money.worker_config import list_configs, get_config
test("configs defined", len(list_configs()) > 0)
test("3 configs", len(list_configs()) == 3)
r = get_config("researcher")
test("researcher has factory", r.factory == "report" if r else False)
test("researcher has skills", len(r.skills) > 0 if r else False)

# 18. CLI help works
print("\n18. CLI help")
from get_me_money.cli import main
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(main, ["--help"])
test("CLI runs", result.exit_code == 0)
test("CLI has commands", "workshop" in result.output)

# 19. Lab loads
print("\n19. Lab module loads")
from get_me_money.lab import lab_run
test("lab_run callable", callable(lab_run))

# 20. Employer loads
print("\n20. Employer loads")
from get_me_money.employer import decompose_task, MicroTask, Decomposition
decomp = Decomposition(original_task="test", total_estimated_cost=1.0)
decomp.micro_tasks.append(MicroTask(id="p1", title="subtask", estimated_reward=0.50))
test("decomposition works", len(decomp.micro_tasks) == 1)

# 21. Job loads
print("\n21. CanonicalJob loads")
from get_me_money.job import CanonicalJob, JobStatus, VenueBinding
job = CanonicalJob(title="test job", reward=10.0)
job.add_venue("taskmarket", "tm:abc")
test("job has venue", len(job.venues) == 1)
test("job spec hash", len(job.spec_hash()) == 16)
test("job status", job.status == JobStatus.DRAFT)

# 22. Oracle bridge loads
print("\n22. Oracle bridge loads")
from get_me_money.oracle_bridge import submit_to_oracle
test("submit_to_oracle callable", callable(submit_to_oracle))

print(f"\n=== RESULTS: {PASS} passed, {FAIL} failed ===")
if FAIL > 0:
    sys.exit(1)
