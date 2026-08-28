# Production Audit: WorkerKit Reality Check

**Date:** 2026-08-28
**Verdict:** Real external-submission harness, not yet a reliable WorkerKit.

---

## Current state (honest)

| Area | State | Verdict |
|---|---|---|
| Discover work | Real adapters + dedupe | REAL |
| Economic ranking | Real, outcome-calibrated | REAL but crude |
| Taskmarket submission | Real CLI + legal gate + pre-submit refetch | GOOD |
| Hermes execution | Real Hermes subprocess | REAL |
| Job isolation | Real job-specific workspace/home | GOOD |
| CapabilityBroker | Declares skills needed | Mostly fake |
| Skill acquisition | Doesn't actually install | NOT WIRED |
| Task understanding | Keyword categorization/bundles | TOO BRITTLE |
| Pre-submit verifier | Formatting/length heuristics | NOT TRUSTWORTHY |
| Human queue | Good subsystem | NOT WIRED INTO EXECUTOR |
| Economic memory | Beta-binomial outcome calibration | GOOD |
| Procedural memory | Essentially absent | NOT WIRED |
| WorkRun | Good proposed schema | MOST TRACE FIELDS EMPTY |
| WorkRun hashing | Doesn't hash the output | WRONG |
| Worker tests | One smoke test | NOWHERE NEAR ENOUGH |

---

## The production loop

```
OPPORTUNITY → JOB SPEC → WIN PLAN → CAPABILITIES → BUILD CANDIDATE
→ INDEPENDENT JUDGE → REVISE if needed → SUBMIT → OUTCOME → LEARN
```

---

## Implementation order

1. Replace category/bundle execution with JobSpec → WinPlan
2. Replace Verifier with deterministic checks + isolated rubric Judge
3. Add one revise loop (candidate → judge → revise → final judge)
4. Actually install skills via Hermes native stack
5. Use persistent single Hermes worker profile during testing
6. Wire HumanQueue into Executor with PAUSED_HUMAN → RESUME
7. Make WorkRun real (store JobSpec, WinPlan, candidates, JudgeReports, hashes)
8. Fix Repute lifecycle (WorkRun first, Receipt after outcome, Product after rights check)
9. Wire post-outcome learning (approve staged memory/skill changes)
10. Build real integration tests

---

## The critical test

```
real task
→ correct JobSpec
→ sensible WinPlan
→ actual skills installed
→ artifact
→ deliberately harsh judge
→ revision
→ all hard gates green
→ external submission
→ WorkRun preserved
→ outcome reconciled
→ memory/skill learning staged
```

That's WorkerKit v0.1.
