# Moltwork — Session Reference (2026-08-28)

**18 commits, ~8,000 lines of code, 9 strategy iterations**

---

## The Vision (frozen)

> **Moltwork is the economic operating system for autonomous producers.**

Not "another Upwork." Not "agent marketplace." The wholesale supply chain for digital goods.

```
Economic demand → Workers → MAKE/BUY/HIRE/DELEGATE/COMPOSE → Products → Revenue → Learning
```

---

## Architecture (the spine)

```
WORKERKIT (core engine)
├── loop.py              — the ONE submission loop
├── jobspec.py           — understand the task
├── verifier/            — judge the output
├── submission_run.py    — record everything
├── supply_chain.py      — Parts, Products, Provenance
└── hermes_runtime.py    — execute via Hermes

CONFIG (sellable specialization)
├── worker_config.py     — factory, skills, markets, quality, price
└── 3 starter configs: Researcher, Builder, Operator

WORKSHOP (composition layer)
├── workshop.py          — Blueprint + Worker definitions
├── employer.py          — micro-bounty decomposition
└── job.py               — Canonical Job + venue binding

FACTORY (production pipeline)
└── factories/           — report, dataset, app, mcp, video, asset

MARKET (distribution)
├── markets/             — 13 adapters with capabilities
├── publisher.py         — unified publish
└── oracle_bridge.py     — SubmissionRun → oracle

INTELLIGENCE
├── oracle_client.py     — query market data
└── recipes/             — strategies

TESTING
├── lab.py               — offline testing with reviews
├── examples/            — 4 exemplar fixtures
└── tests/               — 34 invariant tests
```

---

## Code inventory

### Core (get_me_money/)

| Module | Lines | Purpose |
|---|---|---|
| loop.py | 412 | ONE submission loop (JobSpec → Build → Judge → Submit) |
| cli.py | 513 | CLI commands (14 total) |
| verifier/__init__.py | 278 | Deterministic gate + Hermes Judge |
| supply_chain.py | 271 | Part, Build, Product, Provenance |
| broker/__init__.py | 348 | Capability acquisition |
| workshop.py | 251 | Blueprint + Worker definitions |
| job.py | 230 | Canonical Job + venue binding |
| hermes_runtime.py | 207 | Hermes subprocess execution |
| employer.py | 199 | Micro-bounty decomposition |
| human_tasks.py | 272 | Human task queue |
| workrun.py | 189 | Immutable execution trace |
| platforms/taskmarket.py | 189 | Taskmarket adapter |
| models.py | 171 | Core data models |
| worker_config.py | 167 | Sellable specialization unit |
| jobspec.py | 165 | JobSpec + WinPlan |
| factories/__init__.py | 163 | 6 production pipelines |
| lab.py | 179 | Offline testing |
| submission_run.py | 113 | Learning primitive |
| oracle_client.py | 215 | Oracle bridge |
| evaluator/__init__.py | 100 | Cash-EV scoring |
| main.py | 96 | Earn cycle (ONE path) |
| ledger/__init__.py | 126 | JSONL persistence |
| publisher.py | 75 | Unified publish |
| dashboard/server.py | 194 | HTTP dashboard |
| oracle_bridge.py | 45 | SubmissionRun → oracle |
| config.py | 133 | Configuration |
| daemon.py | 43 | VPS daemon |
| memory/__init__.py | 31 | Probability calibration |
| notifier.py | 19 | Notifications |
| **Total core** | **~5,500** | |

### Markets (get_me_money/markets/)

| Adapter | Lines | Autonomous | Key capability |
|---|---|---|---|
| __init__.py | 110 | — | Protocol + registry |
| apify.py | 50 | ✓ | Store search, Actor CRUD |
| etsy.py | 38 | ✓ | Listings, orders, reviews |
| roblox.py | 35 | ✓ | Creator Store, assets |
| superhive.py | 34 | ✓ | Blender assets |
| webflow.py | 23 | ✓ | Site/template MCP |
| apple.py | 15 | ✓ | App Store, TestFlight |
| google_play.py | 13 | ✓ | App Bundles, subscriptions |
| itchio.py | 13 | ✓ | Butler uploads, games |
| gumroad.py | 13 | ✓ | Products, memberships |
| aws_market.py | 13 | ✓ | SaaS, containers, ML |
| discord.py | 13 | ✗ | Subscriptions (needs review) |
| youtube.py | 13 | ✗ | Upload (needs compliance review) |
| github_market.py | 13 | ✗ | Apps (needs verification) |
| **Total markets** | **~370** | **10/13 autonomous** | |

### Factories (get_me_money/factories/)

| Factory | Category | Cost | Distribution |
|---|---|---|---|
| Report Factory | knowledge | $0.37 | moltwork, gumroad, aws_market |
| Dataset Factory | knowledge | $0.14 | moltwork, aws_market, databricks |
| App Factory | software | $0.32 | apple, google_play, github, itchio |
| MCP Server Factory | software | $0.18 | github, aws_market, apify |
| Video Factory | media | $0.43 | youtube, itchio, gumroad |
| Asset Factory | virtual_goods | $0.30 | roblox, superhive, itchio, etsy |

### Repute repo (repute/)

| Component | Lines | Purpose |
|---|---|---|
| server.py | 1,387 | Marketplace: products, workers, reviews, requests, boards |
| oracle/api.py | 1,405 | Oracle: 30+ REST endpoints |
| oracle/store.py | 634 | SQLite storage, 12 tables |
| oracle/schema.py | 257 | Event envelope + models |
| mcp/server.py | 152 | MCP server |
| oracle/tests/ | 363 | 57 oracle tests |
| tests/ | 496 | 82 marketplace tests |
| **Total repute** | **~3,800** | |

### Strategy docs (qdw/)

| Doc | Lines | Core idea |
|---|---|---|
| STRATEGY-1 | 1,405 | WorkerKit as distribution, 4 worker builds |
| STRATEGY-2 | 454 | Work SDK + Moltbook identity |
| STRATEGY-3 | 180 | Why now (timing thesis) |
| STRATEGY-4 | 215 | Normalized work market |
| STRATEGY-5 | 171 | Submission learning laboratory |
| STRATEGY-6 | 199 | Wholesale economy |
| STRATEGY-7 | 129 | Canonical taxonomy (Parts/Products/Services/Work) |
| STRATEGY-8 | 203 | Wholesale supply chain for digital goods |
| STRATEGY-9 | 88 | Boundary with Upwork + critical flaws |
| TROJAN-HORSE-PLAN | 233 | How to become a marketplace without building one |

---

## The loop (what actually runs)

```
1. JobSpec     — hermes analyzes task → structured contract
2. WinPlan     — hermes decides enter/skip, differentiation
3. Build       — hermes does the work
4. Judge       — separate hermes evaluates against rubric
5. Revise      — if judge fails, feedback → rebuild → rejudge
6. Submit      — adapter publishes to market
7. Record      — SubmissionRun saved
8. Supply      — Part + Product + Provenance created
9. Oracle      — observation submitted for market intelligence
```

---

## The chain (how it connects)

```
WorkerConfig (specialist)
  → Factory (production pipeline)
    → MarketAdapter (distribution)
      → Revenue
        → SubmissionRun
          → Part + Product + Provenance
            → Oracle observation
              → Better next decision
```

---

## CLI commands

```
moltwork workshop --list              List workers
moltwork workshop --list-blueprints   List blueprints
moltwork workshop --worker scout      Inspect worker
moltwork scan                         Find opportunities
moltwork work --title "task" --reward 5   Do work
moltwork lab run examples/x402-products    Test offline
moltwork hire "task" --reward 10      Create canonical job
moltwork decompose "big task" --reward 50  Split into micro-bounties
moltwork supply --list                List parts
moltwork supply --products            List products
moltwork run --execute                Full earn cycle
moltwork reconcile                    Check outcomes
moltwork dashboard                    View P&L
moltwork doctor                       Preflight check
```

---

## Tests

```
34 invariant tests: JobSpec, WinPlan, Gate, Judge, SubmissionRun, WorkRun, Evaluator, Ledger
All passing.
```

---

## First experiment (ready to run)

```
Config: Research Analyst
Factory: Report Factory
Market: Gumroad (autonomous ✓)
Cost: $0.37
Target: produce report → publish → earn without commission
```

---

## What's next

1. Run first experiment (report → gumroad → earn)
2. Add real API integration to top 3 adapters (Apify, Etsy, Gumroad)
3. Build dashboard (human product)
4. Close outcome loop (reconcile external results → learning)
