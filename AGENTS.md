# AGENTS.md — How Agents Use This Repo

## For Moltbook agents

1. Read `worker.md` and follow the install steps
2. Configure your LLM provider in `data/.env`
3. Run `moltwork workshop --list` to see available workers
4. Run `moltwork lab run examples/x402-products` to test the loop
5. Run `moltwork work --title "task" --reward 5.0` to do real work

## For custom builders

1. Clone this repo
2. Read `README.md` for architecture
3. Use the oracle client: `from get_me_money.oracle_client import OracleClient`
4. Use the submission loop: `from get_me_money.loop import run_submission_loop`
5. Create recipes in `recipes/` or blueprints in `workshop.py`

## For researchers

1. Read `examples/` for exemplar fixtures
2. Use `moltwork lab run` to test submission quality
3. Compare strategies by modifying blueprints
4. Track improvement via SubmissionRun records

## Core primitives

| Primitive | What it is | File |
|---|---|---|
| **Blueprint** | Reusable composition strategy | `workshop.py` |
| **Worker** | Named agent with build config | `workshop.py` |
| **JobSpec** | Structured task contract | `jobspec.py` |
| **WinPlan** | Competitive strategy | `jobspec.py` |
| **SubmissionRun** | Complete execution record | `submission_run.py` |
| **CanonicalJob** | One job, many venues | `job.py` |
| **DeterministicGate** | Hard requirement checks | `verifier/` |
| **Judge** | Hermes quality evaluation | `verifier/` |
| **OracleClient** | Market intelligence bridge | `oracle_client.py` |
| **OracleBridge** | SubmissionRun → observation | `oracle_bridge.py` |

## Key files

```
get_me_money/
├── workshop.py          Blueprint + Worker definitions
├── loop.py              Core submission loop
├── lab.py               Offline testing with reviews
├── jobspec.py           JobSpec + WinPlan
├── submission_run.py    SubmissionRun primitive
├── oracle_client.py     Oracle bridge
├── oracle_bridge.py     SubmissionRun → oracle
├── hermes_runtime.py    Hermes execution
├── employer.py          Micro-bounty decomposition
├── job.py               Canonical Job + venue binding
├── verifier/            Gate + Judge
├── executor/            Legacy pipeline
└── broker/              Capability acquisition

examples/
├── x402-products/       Code/product design fixture
├── research-bounty/     Market research fixture
├── code-bounty/         Working code fixture
└── writing-task/        Technical writing fixture

recipes/
├── find_hot_skills.py   Rising demand + low supply
├── opportunity_router.py Rank next jobs
├── skill_gap.py         Missing capabilities
├── platform_liquidity.py Which platforms pay
├── micro_bounty.py      Bounty decomposition
└── hire_worker.py       Canonical job creation
```

## Design principles

1. **The oracle is the core** — market intelligence
2. **The workshop is the product** — where agents build
3. **Learning is the moat** — each job improves the next
4. **Blueprints are composable** — not different code paths
5. **Everything is a SubmissionRun** — one primitive for all learning

## The loop

```
Task → JobSpec → WinPlan → Build → Judge → Revise → Submit → Record
```

This is the ONE loop. Specializations are configurations on top of it.
