# Strategy Memory

**Derived from:** SubmissionRun records
**Last updated:** 2026-08-28
**Runs completed:** 1 (lab mode, x402 fixture)

---

## What works

### JobSpec generation
- Hermes reliably extracts hard requirements from task briefs
- Scoring criteria mapping is accurate
- Rejection conditions are specific and testable

### Judge evaluation
- Separate Hermes call produces honest scores
- Revision suggestions are specific and actionable
- Gate + Judge two-phase approach catches structural issues first

### Revision loop
- Judge feedback → rebuild → rejudge improves quality
- One revision round is usually sufficient for structured tasks

---

## What doesn't work yet

### Skill acquisition
- Skills are declared but never installed
- Need to wire Hermes native skill discovery

### Competition awareness
- WinPlan doesn't yet analyze actual competition
- Entry decisions are generic

### Post-outcome learning
- No postmortem system yet
- Strategy memory is manually maintained

---

## Observed patterns

### For structured bounties (explicit rubric + rejection conditions)
1. Parse every hard requirement into JobSpec
2. Map scoring criteria to weighted rubric
3. Check rejection conditions before building
4. Build with rubric weights in context
5. Judge against rubric, not generic quality

### For open-ended tasks
1. Focus on completeness and structure
2. Include sources and evidence
3. Address all visible requirements
4. Differentiate from generic responses

---

## Proposed process improvements

1. **Add competition analysis to WinPlan** — check submission count before entering
2. **Wire Hermes skills** — install relevant skills before building
3. **Add postmortem** — after external outcome, analyze what worked/didn't
4. **Track skill effectiveness** — which skills correlate with acceptance
5. **Build fixture corpus** — 10+ exemplar tasks for benchmarking

---

## Skill effectiveness (pending data)

| Skill | Runs | Wins | Win rate |
|---|---|---|---|
| (no data yet) | — | — | — |

---

## Worker build versions

| Version | Config | Notes |
|---|---|---|
| default-v1 | hermes, 1 candidate, 1 revision | Current baseline |

---

## Lessons

- (none yet — need real external outcomes)
