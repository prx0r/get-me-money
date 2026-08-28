# Moltwork WorkerKit

**From agent to paid worker in one click.**

WorkerKit is the SDK that turns any existing AI agent into a paid worker. It discovers opportunities across 60+ agent-earning platforms, evaluates expected value, executes work via Hermes, verifies output, submits to platforms, and records the full execution trace.

## Quick Start

```bash
# Install
pip install -e .

# Scan for opportunities
moltwork scan

# Dry run (see ranked opportunities)
moltwork run

# Execute (actually do work and submit)
moltwork run --execute

# Check P&L
moltwork dashboard
```

## Architecture

```
FIND WORK → CHOOSE → WORK → VERIFY → SUBMIT → GET PAID → LEARN
```

| Component | What it does |
|---|---|
| **Platforms** | Discover opportunities from Taskmarket, TryBounty, Superteam, MoltJobs |
| **Evaluator** | Cash-EV scoring with beta-binomial probability calibration |
| **Broker** | Capability acquisition, skill bundles, isolated Hermes environments |
| **Executor** | 8-step lifecycle: claim → plan → execute → verify → submit |
| **Hermes Runtime** | Spawns Hermes subprocess with isolated env and security boundary |
| **Verifier** | Independent quality gate (blind to builder reasoning) |
| **Ledger** | Append-only JSONL store with dedup and reconciliation |
| **Memory** | Beta-binomial probability calibration from past outcomes |

## Config

Config lives in `data/config.json`:

```json
{
  "budget": {
    "daily_cap": 5.0,
    "per_attempt_cap": 2.0,
    "min_reward": 0.5,
    "min_ev": 0.1
  },
  "hermes": {
    "provider": "opencode-go",
    "model": "mimo-v2.5",
    "home": "/root/.hermes-gmm"
  }
}
```

Credentials go in `data/.env`:

```
OPENCODE_GO_API_KEY=sk-...
```

## How It Works

1. **Scan** — Query platform APIs for open tasks/bounties
2. **Evaluate** — Score each opportunity: `P(success) × reward × (1 - fee) - cost`
3. **Rank** — Sort by expected value, filter by budget gates
4. **Claim** — Check eligibility on the platform
5. **Build Profile** — Broker creates isolated Hermes workspace with required skills
6. **Execute** — Hermes runs the task in one-shot mode with security boundary
7. **Verify** — Independent quality check on deliverables
8. **Submit** — Platform CLI/API submission
9. **Record** — Save attempt to ledger with full metadata
10. **Reconcile** — Check submission status, record outcome

## Status

**First external submission made:** Taskmarket survey ($1.50 USDC)
- submissionId: `c434732c-7286-42a7-a660-a5cdb9362528`
- Status: PENDING (awaiting owner review)

**Pipeline status:**
- Steps 1-5: Working
- Step 6: Working (fixed: hermes content extraction)
- Steps 7-10: Untested end-to-end

## Development

```bash
# Run smoke tests
python tests/smoke.py

# Check doctor (preflight)
moltwork doctor
```

## Project Structure

```
get_me_money/
├── cli.py              # Click CLI
├── main.py             # Earn cycle orchestration
├── config.py           # Configuration loading
├── models.py           # Core data models
├── evaluator/          # Cash-EV scoring
├── executor/           # Execution lifecycle
├── broker/             # Capability acquisition
├── hermes_runtime.py   # Hermes subprocess
├── verifier/           # Quality gate
├── ledger/             # Append-only JSONL
├── memory/             # Probability calibration
├── platforms/          # Platform adapters
│   ├── taskmarket.py   # Taskmarket CLI
│   ├── bounty.py       # TryBounty API
│   ├── superteam.py    # Superteam Earn API
│   └── moltjobs.py     # MoltJobs API
├── workrun.py          # Execution trace
├── human_tasks.py      # Human escalation queue
├── notifier.py         # Notifications
├── dashboard/          # P&L + HTTP server
└── daemon.py           # VPS daemon
```

## License

MIT
