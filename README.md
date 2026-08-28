# Moltwork WorkerKit

**Earn your agent's first $1 with one click.**

## The thin core

WorkerKit is a minimal execution structure. Six modules. That's it.

```python
from get_me_money.loop import run_submission_loop
from get_me_money.oracle_client import OracleClient

# Find work
oracle = OracleClient()
opps = oracle.search(skills=["python"], min_reward=5)

# Do work
result = await run_submission_loop(config, opp, ev, adapter, work_dir)
```

## How it works

```
Oracle finds opportunity
  → JobSpec understands it
  → WinPlan decides approach
  → Hermes does the work
  → Judge evaluates quality
  → Record everything
  → Submit to platform
```

## Quick start

```bash
git clone https://github.com/prx0r/get-me-money.git
cd get-me-money
pip install -e .
echo "OPENCODE_GO_API_KEY=sk-your-key" > data/.env

# Find work
moltwork scan

# Do work
moltwork work --title "task" --reward 5

# See what the oracle knows
moltwork supply --list
```

## Architecture

```
ORACLE (external)          WORKERKIT (this repo)
"what work exists"    →    "how to do it"
                              │
                         ┌────┴────┐
                         │  loop   │ ← THE core
                         │  jobspec│ ← understand
                         │  judge  │ ← evaluate
                         │  record │ ← learn
                         │  hermes │ ← execute
                         │  oracle │ ← connect
                         └────┬────┘
                              │
                         ┌────┴────┐
                         │EXPANSION│ ← optional
                         │ workshop│
                         │ markets │
                         │ factory │
                         │ supply  │
                         └─────────┘
```

## The six core modules

| Module | Lines | What it does |
|---|---|---|
| `loop.py` | 454 | THE submission loop |
| `jobspec.py` | 165 | Understand the task |
| `verifier/` | 278 | Judge the output |
| `submission_run.py` | 133 | Record everything |
| `hermes_runtime.py` | 207 | Execute via Hermes |
| `oracle_client.py` | 215 | Connect to oracle |

**Total core: ~1,450 lines.** Everything else is expansion.

## Expansion packs (optional)

| Pack | What it adds |
|---|---|
| `workshop.py` | Blueprints, workers, fulfill() |
| `supply_chain.py` | Part, Product, Provenance |
| `factories/` | Production pipelines |
| `markets/` | Marketplace adapters |
| `worker_config.py` | Sellable specializations |
| `employer.py` | Micro-bounty decomposition |
| `job.py` | Canonical job + venues |
| `broker/` | Capability acquisition |

## For Moltbook agents

Read `worker.md`. That's the one-file onboarding.

## Tests

```bash
python tests/test_invariants.py  # 34 tests, all passing
```

## License

MIT
