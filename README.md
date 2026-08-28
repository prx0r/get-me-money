# Moltwork WorkerKit

**From agent to paid worker. The work SDK for the agent economy.**

WorkerKit gives agents the professional work loop: understand the task, plan the approach, do the work, judge quality, revise if needed, submit, and learn. The oracle provides market intelligence. The submission loop does the work. Together they form a worker that gets better with each job.

## The Vision

```
Install WorkerKit
    ↓
Query the oracle (what work exists?)
    ↓
Find the best opportunity for YOUR capabilities
    ↓
Understand the task (JobSpec)
    ↓
Plan how to win (WinPlan)
    ↓
Do the work (Hermes)
    ↓
Judge quality (independent Hermes call)
    ↓
Revise if needed
    ↓
Submit
    ↓
Record everything (SubmissionRun)
    ↓
Learn from outcome
    ↓
Next job is better
```

## Quick Start

```bash
# Install
git clone https://github.com/prx0r/get-me-money.git
cd get-me-money
pip install -e .

# Configure
echo "OPENCODE_GO_API_KEY=sk-your-key" > data/.env

# Test offline (no wallet needed)
moltwork lab run examples/x402-products

# Find work
moltwork scan

# Do work
moltwork work --title "Your task" --reward 5.0
```

## For Moltbook Agents

Read `worker.md` — it's the one-file onboarding document. Your agent reads it, installs WorkerKit, and starts working.

## Architecture

```
ORACLE                    SUBMISSION LOOP              LEARNING
(what work exists)   →    (how to win it)         →    (what worked)
                              
Market intelligence       Task → JobSpec → WinPlan       SubmissionRun
Opportunities             Build → Judge → Revise         Strategy memory
Demand signals            Submit → Record                Postmortem
Skill trends
```

### The Oracle (market intelligence)

The oracle provides:
- What work exists across platforms
- What it pays
- Which skills are in demand
- How competitive each market is
- Trend analysis and demand signals

```python
from get_me_money.oracle_client import OracleClient

oracle = OracleClient()
opps = oracle.search(skills=["python", "research"], min_reward=10)
trending = oracle.trending_skills()
```

### The Submission Loop (doing the work)

Given a task, the loop produces the best possible submission:

```python
from get_me_money.loop import run_submission_loop
from get_me_money.models import Opportunity, Evaluation

result = await run_submission_loop(config, opp, ev, adapter, work_dir)
```

Steps:
1. **JobSpec** — Hermes analyzes the task → structured requirements + scoring + rejection conditions
2. **WinPlan** — Hermes decides enter/skip, differentiation strategy, candidate count
3. **Build** — Hermes does the work with full context
4. **Judge** — Separate Hermes call evaluates against the rubric
5. **Revise** — If judge fails, feedback → rebuild → rejudge
6. **Record** — SubmissionRun saved with all versions + judge reports

### Learning (what worked)

Each job produces a SubmissionRun:

```yaml
task: {title, reward, platform}
jobspec: {objective, requirements, scoring, rejection}
strategy: {differentiator, candidates, revisions}
candidates:
  - v1: {content, judge_score, failures}
  - v2: {content, judge_score, failures}
external: {status, score, rank, feedback}
lessons: [what worked, what didn't]
```

Over time, strategy-memory.md is derived from completed runs.

## Recipes

Pre-built strategies in `recipes/`:

```python
from recipes.find_hot_skills import find_hot_skills
from recipes.opportunity_router import route_opportunities
from recipes.skill_gap import analyze_skill_gaps

# What skills pay most?
hot = find_hot_skills(min_reward=50)

# What should I work on next?
ranked = route_opportunities(skills=["solidity"], min_reward=100)

# What skill am I missing?
gaps = analyze_skill_gaps(agent_skills=["python", "web"])
```

Write your own recipes — the oracle + submission loop are your building blocks.

## Exemplar Fixtures

Test the loop offline with known tasks:

```bash
moltwork lab run examples/x402-products
```

Each fixture contains:
- `task.md` — the original brief
- `runs/` — SubmissionRun records
- `bad/` — intentionally broken submissions (for testing the gate)

Add your own fixtures for tasks you've completed. The more fixtures, the better the benchmark.

## Core Primitives

| Primitive | What it is | Why it matters |
|---|---|---|
| **JobSpec** | Structured task contract | Replaces brittle category matching with explicit requirements |
| **WinPlan** | Competitive strategy | Decides whether to enter and how to differentiate |
| **SubmissionRun** | Complete execution record | One primitive for all learning |
| **DeterministicGate** | Hard requirement checks | No LLM needed — file counts, formats, placeholders |
| **Judge** | Hermes quality evaluation | Independent from builder, sees only task + artifact |
| **OracleClient** | Market intelligence bridge | Connects submission loop to market data |

## Config

`data/config.json`:
```json
{
  "budget": {"daily_cap": 5.0, "per_attempt_cap": 2.0, "min_reward": 0.5},
  "hermes": {"provider": "opencode-go", "model": "mimo-v2.5"}
}
```

`data/.env`:
```
OPENCODE_GO_API_KEY=sk-...
```

## Project Structure

```
get_me_money/
├── loop.py              Core submission loop
├── lab.py               Offline testing
├── jobspec.py           JobSpec + WinPlan
├── submission_run.py    SubmissionRun primitive
├── oracle_client.py     Oracle bridge
├── hermes_runtime.py    Hermes execution
├── verifier/            Gate + Judge
├── executor/            Legacy pipeline
├── evaluator/           EV scoring
├── broker/              Capability acquisition
├── ledger/              JSONL persistence
├── memory/              Probability calibration
├── platforms/           Platform adapters
└── cli.py               CLI commands

examples/
└── x402-products/       Exemplar fixture

recipes/
├── find_hot_skills.py
├── opportunity_router.py
├── skill_gap.py
└── platform_liquidity.py

worker.md                One-click onboarding
AGENTS.md                How agents use this
```

## Development

```bash
# Lab mode (offline)
moltwork lab run examples/x402-products

# Tests
python tests/smoke.py

# Doctor
moltwork doctor
```

## Status

- First external submission: Taskmarket survey ($1.50 USDC, pending)
- Core loop: JobSpec → WinPlan → Build → Judge → Revise working
- Oracle bridge: connected to repute/oracle dataset
- 4 starter recipes: hot skills, opportunity routing, skill gaps, liquidity

## License

MIT
