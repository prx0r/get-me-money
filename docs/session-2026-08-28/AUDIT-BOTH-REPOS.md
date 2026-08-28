# Audit: get-me-money + repute

**Date:** 2026-08-28
**Status:** Both repos reviewed, docs moved from qdw/ to correct locations

---

## get-me-money — The Worker Kit

```
49 Python files | 6,850 lines | 34 tests passing
```

### Core (34 modules)

| Module | Lines | Status |
|---|---|---|
| loop.py | 454 | THE submission loop — JobSpec → Build → Judge → Submit |
| cli.py | 542 | 16 CLI commands |
| main.py | 167 | scan_all + reconcile_pending + earn_cycle |
| verifier/__init__.py | 278 | Deterministic gate + Hermes Judge |
| broker/__init__.py | 348 | Capability acquisition |
| supply_chain.py | 274 | Part, Product, Provenance |
| workshop.py | 331 | Blueprint, Worker, fulfill() |
| human_tasks.py | 272 | Human task queue |
| hermes_runtime.py | 207 | Hermes subprocess |
| job.py | 230 | Canonical Job + venue binding |
| oracle_client.py | 215 | Bridge to repute oracle |
| employer.py | 199 | Micro-bounty decomposition |
| workrun.py | 189 | Execution trace |
| lab.py | 179 | Offline testing |
| jobspec.py | 165 | JobSpec + WinPlan |
| worker_config.py | 167 | Sellable specialization |
| factories/__init__.py | 163 | 6 production pipelines |
| models.py | 171 | Core data models |
| submission_run.py | 133 | Learning primitive |
| ledger/__init__.py | 126 | JSONL persistence |
| config.py | 133 | Configuration |
| evaluator/__init__.py | 100 | Cash-EV scoring |
| publisher.py | 75 | Unified publish |
| dashboard/server.py | 194 | HTTP dashboard |
| oracle_bridge.py | 45 | SubmissionRun → oracle |
| memory/__init__.py | 31 | Probability calibration |
| daemon.py | 43 | VPS daemon |
| notifier.py | 19 | Notifications |

### Markets (13 adapters)

| Adapter | Lines | Autonomous | Verified |
|---|---|---|---|
| apify.py | 85 | ✓ | ✓ (3 contract tests) |
| etsy.py | 38 | ✓ | stub |
| roblox.py | 35 | ✓ | stub |
| superhive.py | 34 | ✓ | stub |
| webflow.py | 23 | ✓ | stub |
| apple.py | 15 | ✓ | stub |
| google_play.py | 13 | ✓ | stub |
| itchio.py | 13 | ✓ | stub |
| gumroad.py | 13 | ✓ | stub |
| aws_market.py | 13 | ✓ | stub |
| discord.py | 13 | ✗ | stub |
| youtube.py | 13 | ✗ | stub |
| github_market.py | 13 | ✗ | stub |

### Tests

| File | Lines | What |
|---|---|---|
| test_invariants.py | 243 | 34 invariant tests (all passing) |
| smoke.py | 23 | Basic smoke test |

### Docs

| Location | What |
|---|---|
| README.md | Architecture, quick start, workers, blueprints |
| worker.md | One-click onboarding |
| AGENTS.md | How agents use this |
| docs/northstar/ | 10 research docs (pre-session) |
| docs/strategy/ | 3 strategy docs (pre-session) |
| docs/session-2026-08-28/ | 8 docs (build notes, handover, strategy) |

---

## repute — The Data Layer

```
57 Python files | 11,168 lines | 859 lines of tests
```

### server.py — Marketplace (1,387 lines)

12 DB tables, 35+ routes:
- Products, Workers, Reviews, Requests (bounties), Boards
- Progressive reveal (Merkle commitment, pay-per-chunk)
- Context packs (9 typed products)
- Pricing oracle, demand tracking
- WorkRun endpoint (creates Receipt + Product + Capability)
- Full HTML SPA

### oracle/ — Market Intelligence (3,275 lines)

| File | Lines | What |
|---|---|---|
| api.py | 1,582 | 30+ REST endpoints |
| store.py | 636 | SQLite storage, 12 tables |
| schema.py | 257 | Event envelope + models |
| observations.py | 364 | Diff-and-record with interval bounds |
| merkle.py | 162 | On-chain anchoring |
| cron_ingest.py | 166 | Polling daemon |
| ingest.py | 108 | Normalization pipeline |

### oracle/adapters/ — 25 source adapters

| Adapter | Lines | Source |
|---|---|---|
| rentahuman.py | 284 | RentAHuman |
| the402.py | 233 | The402 |
| bittensor.py | 230 | Bittensor |
| agenthansa.py | 191 | AgentHansa |
| near.py | 190 | NEAR AI |
| bountybook.py | 170 | BountyBook |
| github.py | 168 | GitHub |
| olas_adapter.py | 129 | OLAS |
| agent402.py | 116 | Agent402 |
| x402engine.py | 108 | x402engine |
| algora.py | 104 | Algora |
| payapi.py | 95 | PayAPI |
| moltjobs.py | 92 | MoltJobs |
| mock.py | 86 | Test data |
| superteam.py | 62 | Superteam |
| 13 more | ~600 | Various |

### MCP — Agent-facing tools (965 lines)

14 tools across 6 categories:
- Market: pulse, trends, timeseries
- Opportunities: briefing, search, detail
- Pricing: guide, distribution
- Competition: index, demand gaps
- Sources: quality, health
- Observations: timeline, metrics

### src/ — Marketplace primitives (1,209 lines)

| File | Lines | What |
|---|---|---|
| commitment.py | 337 | Merkle tree, chunking, reveal order |
| reveal.py | 231 | Progressive paid reveal |
| context_pack.py | 252 | 9 typed product schemas |
| mcp.py | 284 | HTTP client + tool defs |
| x402.py | 105 | Payment adapter (stub) |

### Tests (859 lines)

| File | Lines | Coverage |
|---|---|---|
| test_core.py | 264 | Chunking, context packs, pricing, reveal, x402, MCP |
| test_endpoints.py | 232 | Every API endpoint |
| oracle/tests/test_oracle.py | 363 | Oracle store, schema, ingest, observations |

---

## How they connect

```
get-me-money                    repute
    │                              │
    │ oracle_client.py ──────────→ oracle/api.py
    │                              │
    │ oracle_bridge.py ──────────→ oracle/store.py
    │                              │
    │ (future) ←──────────────── server.py (marketplace)
```

**Currently connected:** oracle_client reads opportunities, oracle_bridge sends observations.
**Not connected:** marketplace (products, workers, reviews) is separate.

---

## What's next

1. Wire get-me-money execution → repute marketplace (products, workers)
2. Wire repute MCP tools → get-me-money loop (agent-facing interface)
3. Shared schema: Part, Product, Worker, Receipt
4. One unified API gateway

---

## File locations

**get-me-money:**
- Code: `/root/get-me-money/get_me_money/`
- Tests: `/root/get-me-money/tests/`
- Docs: `/root/get-me-money/docs/`
- Session docs: `/root/get-me-money/docs/session-2026-08-28/`

**repute:**
- Code: `/root/repute/server.py`, `/root/repute/oracle/`, `/root/repute/src/`, `/root/repute/mcp/`
- Tests: `/root/repute/tests/`, `/root/repute/oracle/tests/`
- Docs: `/root/repute/NORTHSTAR*.md`, `/root/repute/*.md`
