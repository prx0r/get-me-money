# Build Notes — 2026-08-28

**Session:** First full day of Moltwork development
**Start:** Audit of two repos (get-me-money + repute)
**End:** 22 commits, ~8,500 lines, 33/33 tests passing

---

## Timeline

### Morning (08:00-10:00 UTC)
- Audited get-me-money (3,400 lines, 30% dead code)
- Audited repute (7,172 lines, oracle + marketplace)
- Archived dead code: repute/__init__.py, moltwork.py, oracle.py
- Fixed hermes-gmm auth (copied .env)
- Fixed config: provider/opencode-go, model/mimo-v2.5
- First manual submission: Taskmarket survey $1.50

### Midday (10:00-12:00 UTC)
- Switched from hermes -z to hermes chat (tool support)
- Built core loop: JobSpec → WinPlan → Build → Judge → Submit
- Built deterministic gate + Hermes Judge
- Built SubmissionRun primitive
- Built lab mode with timestamped reviews
- 34 invariant tests passing

### Afternoon (12:00-14:00 UTC)
- Built supply chain: Part, Product, Provenance
- Built employer mode: micro-bounty decomposition
- Built canonical Job + venue binding
- Built oracle bridge: SubmissionRun → oracle
- Built 5 market adapters (Apify, Etsy, Roblox, Superhive, Webflow)
- Built 4 workshop workers + 4 blueprints
- Built 6 factories
- Polished all documentation

### Late afternoon (14:00-16:00 UTC)
- Added 8 more market adapters (Apple, Google Play, itch, Gumroad, GitHub, AWS, Discord, YouTube)
- Built WorkerConfig (sellable specialization primitive)
- Built Workshop.fulfill() decision engine
- Reviewed strategy 9 times (STRATEGY-1 through STRATEGY-9)
- Peer review identified 10 P0 issues

### Evening (16:00-18:00 UTC)
- Fixed PR-A: restored scan_all + reconcile_pending
- Fixed PR-B: HermesRunner workspace isolation
- Fixed PR-C: cost accounting on CandidateRecord + SubmissionRun
- Fixed PR-D: JobSpec validation + bounded counts
- Fixed PR-F: removed submitted=accepted corruption
- Fixed PR-G: Apify contract tests pass (3/3)
- 33/33 full tests passing

---

## What exists (final state)

### Code (get-me_money/)
```
Core:       ~5,500 lines (15 modules)
Markets:    ~400 lines (13 adapters)
Factories:  ~163 lines (6 factories)
Tests:      33/33 passing
Total:      ~6,000 lines
```

### Key files
- loop.py (412 lines) — THE submission loop
- main.py (135 lines) — scan + reconcile + earn_cycle
- jobspec.py (165 lines) — JobSpec + WinPlan
- submission_run.py (130 lines) — learning primitive
- supply_chain.py (280 lines) — Part, Product, Provenance
- workshop.py (270 lines) — Blueprint, Worker, fulfill()
- worker_config.py (175 lines) — sellable specialization
- hermes_runtime.py (200 lines) — Hermes subprocess
- verifier/ (280 lines) — Gate + Judge
- 13 market adapters
- 6 factories
- 33 invariant tests

### What works end-to-end
- molwork scan (finds opportunities via adapters)
- molwork work (JobSpec → Build → Judge → Submit)
- molwork fulfill (decides MAKE/BUY/HIRE/DELEGATE/COMPOSE)
- molwork workshop (workers + blueprints)
- molwork supply (Parts + Products)
- Apify live search (3/3 contract tests pass)
- Lab mode (offline testing with reviews)

### What doesn't work yet
- Real execution through full loop (hermes timeout on long prompts)
- Apify create/publish (needs API token)
- Gumroad/other adapters (stubs only)
- Workshop.fulfill() is estimate-only, not execution
- No real revenue yet

---

## Architecture (frozen)

```
ORACLE → OPPORTUNITY → WORKERKIT → WORKSHOP → PRODUCT → MARKET → REVENUE
                                                          ↓
                                                    SUBMISSIONRUN
                                                          ↓
                                              Part + Product + Provenance
                                                          ↓
                                                     LEARNING
```

---

## Strategy (9 iterations)

1. WorkerKit as distribution
2. Work SDK + Moltbook identity
3. Why now (timing)
4. Normalized work market
5. Submission learning laboratory
6. Wholesale economy
7. Canonical taxonomy (Parts/Products/Services/Work)
8. Wholesale supply chain for digital goods
9. Boundary with Upwork + critical flaws

**Final thesis:** Moltwork is the economic operating system for autonomous producers.

---

## For next agent

### Critical: read these first
1. `qdw/REFERENCE-2026-08-28.md` — full code inventory
2. `qdw/PRODUCTION-AUDIT-2026-08-28.md` — peer review findings
3. This file (BUILD-NOTES)

### What to do next
1. PR-H: Make fulfill() actually execute MAKE or BUY (not just recommend)
2. 12 real integration tests (not assertion counts)
3. Wire Hermes execution to actually complete a factory run
4. Get one real revenue (Apify Actor or Gumroad product)

### Don't do
- Don't add new marketplaces
- Don't add new factories
- Don't add new workers/blueprints
- Don't touch oracle
- Don't build avatars or 3D

### The rule
> A primitive is not "implemented" because a dataclass or mock exists. It is implemented only when a production-path integration test proves the claimed behavior.
