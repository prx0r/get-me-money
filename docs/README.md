# get-me-money

Agent-native earning station. Crawls multiple bounty/marketplace surfaces, evaluates expected value, executes work within budget, records outcomes, and learns which strategies are profitable.

## Architecture

```
                    EARNING STATION
                         │
            ┌────────────┴─────────────┐
            │                          │
        ACTIVE WORK                PRODUCTS
            │                          │
      TryBounty                    x402
      Algora                       ACP
      Opire                        Olas
      Clustly                      paid MCP
      Superteam                    paid APIs
            │                          │
            └────────────┬─────────────┘
                         ↓
                 OPPORTUNITY DB
                         ↓
                     EVALUATOR
                  (EV scoring)
                         ↓
                      EXECUTOR
                  (claim → work → submit)
                         ↓
                     VERIFIER
                         ↓
                       P&L
                         ↓
                      MEMORY
                         ↓
                     LEARNING
                         ↺
```

## Quick start

```bash
# Scan all platforms for opportunities
python3 -m get_me_money.cli scan

# Full cycle: scan → evaluate → attempt → record (dry run)
python3 -m get_me_money.cli run --dry-run

# Full cycle with execution
python3 -m get_me_money.cli run

# View P&L dashboard
python3 -m get_me_money.cli dashboard

# View learned strategies
python3 -m get_me_money.cli strategies

# Health check all adapters
python3 -m get_me_money.cli health
```

## Configuration

Settings live in `data/config.json`. Budget controls:

```json
{
  "budget": {
    "daily_cap": 5.00,
    "per_attempt_cap": 2.00,
    "lifetime_cap": 50.00,
    "min_reward": 1.00,
    "min_ev": 0.50
  }
}
```

Platform API keys go in environment variables:

```bash
export BOUNTY_API_KEY="..."
export ALGORA_TOKEN="..."
export OPIRE_TOKEN="..."
export CLUSTLY_TOKEN="..."
export SUPERTEAM_KEY="..."
```

## Platforms

| Platform | Status | Why |
|----------|--------|-----|
| TryBounty | Active | Best agent-native opportunity now |
| Algora | Active | Serious GitHub bounties ($50-$2500) |
| Opire | Active | Similar to Algora |
| Clustly | Active | Agent-native marketplace, 4% fee |
| Superteam | Active | High-value bounties ($500-$5k) |
| gigs.sh | Discovery | 46-platform directory, not a job board |

## EV Formula

$$
EV_{total} = P(success) \times reward - cost + EV_{learning} + EV_{reusable}
$$

The key insight: a $20 task that teaches the agent how to create a reusable $0.03/call API is worth more than a one-off $40 job.

## Data

All data persists in `data/` as JSONL:
- `opportunities.jsonl` — all discovered opportunities
- `attempts.jsonl` — execution history with outcomes
- `strategies.jsonl` — learned per-category/per-platform performance
- `dashboard.json` — latest P&L snapshot
