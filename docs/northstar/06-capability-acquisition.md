# NORTHSTAR 6 — Capability Acquisition Layer + Skill Broker
**Date:** 2026-08-28 (sixth pass)
**Source:** Hermes Skills Hub (90,700 skills), SkillMake (260 curated), platform skill.md adoption

---

## Core insight

The earning agent doesn't need to already know how to do every paid job. It only needs to know how to:
1. Recognize a profitable job
2. Acquire trustworthy capabilities for it
3. Prove it completed the work correctly
4. Remember which capability combinations made money

## The new loop

```
DISCOVER → JOB COMPILER → CAPABILITY GAP → SKILL BROKER → REPO SCOUT
→ SECURITY/LICENSE GATE → BUILD JOB-SPECIFIC PROFILE → PLAN → EXECUTE
→ INDEPENDENT VERIFIER → SUBMIT → RECONCILE → UPDATE MEMORY
```

## Skill sources (trust order)

1. Hermes built-in
2. Hermes official
3. Anthropic / OpenAI / NVIDIA verified
4. SkillMake reviewed (260 skills, pinned hashes)
5. reputable GitHub sources
6. skills.sh community
7. other community registries

## Security reality

NVIDIA SkillSpector: 26.1% of 42,447 skills had vulnerabilities, 5.2% showed likely malicious intent.

Acquisition must be:
```
SEARCH → DOWNLOAD TO QUARANTINE → inspect source + provenance
→ SkillSpector → HIGH/CRITICAL? → reject → install into JOB-SPECIFIC profile
```

## Per-job isolation

```
/jobs/
  taskmarket-abc123/
      hermes-home/     (isolated profile)
      workspace/
      references/
      artifacts/
      plan/
      security/
```

Each job gets its own Hermes profile with only the skills it needs.

## Skill performance tracking

Don't just track "research jobs win 25%". Track:
- Per-skill win rate
- Per-skill avg compute cost
- Per-skill avg net
- Per-bundle performance

The agent learns which SKILL COMBINATIONS make money.

## CapabilityBroker (to build)

Given a job brief, produces:
- Required capabilities
- Already available (Hermes built-ins)
- Need to acquire (from SkillMake/Skills Hub)
- Security review results

## Skill bundles by job type

**Code bounty:** github-repo-management, github-issue-to-pr, superpowers, mp-diagnose, mp-tdd, mp-code-review, github-pr-workflow

**Research bounty:** mp-research, prospecting/competitor-profiling, knowledge-work-data, web_search, web_extract

**Web-app bounty:** superpowers, mp-implement, mp-tdd, design-taste-frontend, playwright-skill, wrangler, github-pr-workflow

## Agent can CREATE new skills

Hermes /learn + skill_manage. If repeated workflow isn't covered, create local skill, test against previous jobs, promote if better.

## Independent verifier

Don't let builder verify own work. Judge gets only: original brief, acceptance criteria, final artifact, test output. Not builder's reasoning.

## Platform skill.md adoption

Taskmarket: `npx skills add ... --skill taskmarket`
Superteam: official Agent Skill with register/discover/submit/monitor

This reduces adapter maintenance — read skill.md instead of building custom adapters.
