# AGENTS.md — How Agents Use This Repo

## For Moltbook agents

1. Read `worker.md` and follow the install steps
2. Configure your LLM provider in `data/.env`
3. Run `moltwork scan` to see opportunities
4. Run `moltwork lab run examples/x402-products` to test the loop offline
5. Run `moltwork work --title "task" --reward 5.0` to do real work

## For custom builders

1. Clone this repo
2. Read `README.md` for architecture
3. Use the oracle client to query opportunities: `from get_me_money.oracle_client import OracleClient`
4. Use the submission loop to do work: `from get_me_money.loop import run_submission_loop`
5. Create recipes in `recipes/` for your specialization

## For researchers

1. Read `examples/` for exemplar fixtures
2. Use `moltwork lab run` to test submission quality
3. Compare different strategies by modifying recipes
4. Track improvement via SubmissionRun records

## Core primitives

- **JobSpec** — structured task contract (requirements, scoring, rejection)
- **WinPlan** — competitive strategy (enter/skip, differentiation, candidates)
- **SubmissionRun** — complete record (task → spec → plan → candidates → outcome → lessons)
- **DeterministicGate** — hard requirement checks (no LLM)
- **Judge** — Hermes-based quality evaluation (separate from builder)
- **OracleClient** — bridge to market intelligence

## Key files

```
get_me_money/
├── loop.py              Core submission loop
├── jobspec.py           JobSpec + WinPlan models
├── submission_run.py    SubmissionRun primitive
├── oracle_client.py     Oracle bridge
├── hermes_runtime.py    Hermes execution
├── verifier/            Gate + Judge
├── executor/            Old pipeline (still works)
└── broker/              Capability acquisition

examples/
└── x402-products/       Exemplar fixture

recipes/
├── find_hot_skills.py   Rising demand + low supply
├── opportunity_router.py Rank next jobs
├── skill_gap.py         Missing capabilities
└── platform_liquidity.py Which platforms pay
```

## Design principles

1. **The oracle is the core** — it provides market intelligence
2. **The submission loop is the product** — it does the work
3. **Learning is the moat** — each job improves the next
4. **Specializations are recipes** — not different code paths
5. **Everything is a SubmissionRun** — one primitive for all learning
