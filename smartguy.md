# smartguy.md — Structured Intelligence
**Date:** 2026-08-28
**Sources:** @garrytan, @GeoffreyHuntley, NORTHSTAR research (1-6)

---

# PART 1: KEY INSIGHTS

## 1. The economic thesis

> "Markets contain tasks whose reward is determined by their value to the buyer, while an increasingly capable autonomous agent's cost is determined by compute. Find places where those two numbers diverge."

The spread is the product. Not "another marketplace." Not "another wallet." The brain that finds and exploits the spread.

## 2. AI is a time compression device

> "AI is a time compression device, a fuzzer for ideas that enables a 'Be wrong quickly, be wrong cheaply' way of work/thinking about product development." — @GeoffreyHuntley

Applied to earning: instead of manually testing 50 business ideas, the agent tests 50 earning strategies in a week. The dataset of what works is the real asset.

## 3. The employment landscape shifted

> "in 2025 LLMs got good enough to displace JetBrains/IDEs and in 2026 demonstrable experience in automating your job function and the job function of your colleagues is the new norm to get a job" — @GeoffreyHuntley

The meta-skill is automation. `get-me-money` is literally a demonstration of this.

## 4. Code has personality

> "one of the biggest downsides of an AI generated codebase is that the source code is just so business dry and vanilla. there is something about coming across load bearing comments deep within some modules that is so distinctly human/pure" — @GeoffreyHuntley

Implication for our agent: the submissions that win are the ones with genuine understanding, not synthetic slop. Hermes should produce work that shows comprehension, not just completion.

## 5. The zero-click product

> "Click Launch → receive a persistent economic agent with compute, wallet, identity, skills, job-market connections, spending limits, monitoring, and an objective: earn more than it costs."

Not a dashboard. Not a framework. A product with a single button.

## 6. Capability beats knowledge

The agent doesn't need to already know how to do every paid job. It needs to:
1. Recognize a profitable job
2. Acquire trustworthy capabilities for it
3. Prove it completed the work correctly
4. Remember which capability combinations made money

## 7. Platforms are adopting skill.md

Taskmarket literally tells agents to install its skill. Superteam publishes an official agent skill.md. The adapter maintenance problem is dissolving — read skill.md instead of building custom adapters.

## 8. Security is real

NVIDIA SkillSpector: 26.1% of 42,447 skills had vulnerabilities, 5.2% showed likely malicious intent. Capability acquisition must include quarantine + security scanning.

## 9. Context engineering = malloc

> "mastering llms is all about mastering malloc()" — @GeoffreyHuntley

Every turn, the context window fills with: harness prompt, agent.md, skills, tool calls, responses. Visualizing this as flamegraphs per turn reveals where tokens are being wasted. The agent that manages context most efficiently wins.

## 10. Ephemeral environments > permissions

> "/permission functionality in a harness remains an anti-pattern. it only exists because folks are not doing ephemeral development environments (ie CDE). don't try to constrain the model through what it can access, assume it can access everything and design the operating environment around it." — @GeoffreyHuntley

This validates our per-job isolated Hermes profile approach. Don't restrict the model's tools — restrict the environment.

## 11. ADRs from day 0

> "prompt for the creation of ADR skills from day 0 during planning and the agent will recursively consult/maintain the ADRs during future development/planning sessions." — @GeoffreyHuntley

Architecture Decision Records as persistent skills. The agent remembers WHY it made choices, not just what it built.

## 12. Domain knowledge is the real moat

> "it's strange how one can rebuild a company or products of a company simply through the domain knowledge/experience. something that used to take years can be done in days now, literally days." — @GeoffreyHuntley

Our cross-market opportunity dataset + skill effectiveness data IS domain knowledge. That's the moat.

## 13. Dual verification: static + fuzz

> "playwright provides static visual verification and bombadil provides fuzz based visual verification." — @GeoffreyHuntley

Use both. Playwright for "does it look right." Bombadil for "does it break under random inputs."

## 14. Antithesis skill-pack

> "install the @AntithesisHQ skill-pack if you care about catching correctness faults during development" — @GeoffreyHuntley

For code bounties: correctness checking before submission. Worth evaluating.

---

# PART 2: RELEVANCE TO GET-ME-MONEY

## What this means for the project

| Insight | Implication |
|---------|------------|
| Economic spread thesis | EV evaluator is the core product, not the adapters |
| Time compression | Agent can test 50 strategies/week, building a dataset nobody else has |
| Employment shift | This project IS the "demonstrable experience" — build it publicly |
| Code personality | Hermes submissions must show genuine understanding |
| Zero-click product | `get-me-money` = open-source brain, `earnbox` = consumer product |
| Capability beats knowledge | CapabilityBroker is more important than any single adapter |
| skill.md adoption | Adapter layer can be thin — read platform skill files |
| Security reality | Quarantine + SkillSpector before installing any skill |

## The moat

```
COMMODITY:
Hermes runtime, wallet, skills, job boards

NOT COMMODITY:
cross-market opportunity history
task → capability matching
skill/repo effectiveness data
actual win probabilities
actual execution costs
payment reliability
strategy learning
one-click orchestration
```

The most important dataset: "Given this agent, these skills and this job, what is the probability it can turn $0.17 of compute into a $10 payment?"

---

# PART 3: RECOMMENDED TOOLS & METHODS

## Runtime

| Tool | Purpose | Status |
|------|---------|--------|
| **Hermes Agent** | Worker runtime, skills, Docker isolation, cron, messaging | ✅ installed, v0.20.1 |
| **Nous Portal** | Hermes setup/config | ✅ available |
| **Docker** | Isolated job execution | ⚠️ needs terminal.backend=docker |

## Wallet / Identity

| Tool | Purpose | Status |
|------|---------|--------|
| **Taskmarket CLI** | Wallet + ERC-8004 identity + USDC settlements | ⚠️ needs `npm install -g @lucid-agents/taskmarket` |
| **Ampersend** | Agent wallets, budgets, spend controls, observability | 📋 evaluate for wallet layer |
| **Safe** | Smart account treasury with spending limits | 📋 evaluate for policy enforcement |
| **ERC-8004** | Portable agent identity + reputation | ✅ live on mainnet |
| **Moltbook** | Agent SSO + social identity | 📋 early access |

## Skill Sources (trust order)

| Priority | Source | Notes |
|----------|--------|-------|
| 1 | Hermes built-in | github-*, web_search, browser, plan, file-creator |
| 2 | Hermes official | Skills Hub (90,700 skills) |
| 3 | Anthropic/OpenAI/NVIDIA verified | Major vendor repos |
| 4 | **SkillMake** | 260 curated, pinned hashes, manually reviewed |
| 5 | reputable GitHub | Known good repos with active maintenance |
| 6 | skills.sh community | Community — vet carefully |
| 7 | other registries | ClawHub etc. — **26.1% vulnerability rate** |

## Key Skills (from SkillMake + Hermes)

| Need | Skill | Source |
|------|-------|--------|
| Research | `mp-research` | SkillMake |
| Debug/diagnose | `mp-diagnose` | SkillMake |
| Build from spec | `mp-implement` | SkillMake |
| Test-first | `mp-tdd` | SkillMake |
| Code review | `mp-code-review` | SkillMake |
| Complex decomposition | `mp-wayfinder` | SkillMake |
| Browser testing | `playwright-skill` | SkillMake |
| Prospect research | `prospecting` | SkillMake |
| Competitor research | `competitors`, `competitor-profiling` | SkillMake |
| Full dev workflow | `superpowers` | SkillMake (obra/superpowers) |
| Cloudflare deploy | `wrangler` | SkillMake |
| GitHub PR flow | `github-issue-to-pr`, `github-pr-workflow` | Hermes built-in |
| Data work | `knowledge-work-data` | Anthropic |
| Agent brain/memory | **GBrain** | @garrytan (SOUL.md + 70 skills + PGLite) |

## Earning Platforms (priority order)

| Platform | Status | Daily Income Target | Notes |
|----------|--------|-------------------|-------|
| **TryBounty** | ✅ adapter built | Primary ($5-20/day) | $33.69k escrowed, research/data/datasets |
| **Taskmarket** | ✅ CLI adapter | Continuous ($3-15/task) | Real USDC settlements, 12 open tasks |
| **Superteam** | ✅ API adapter | Background/jackpot | $290 Terminal 3 challenge, discovery only |
| Algora | 📋 disabled | $50-2500/bounty | Needs verified API contract |
| Opire | 📋 disabled | $50-500/bounty | Needs verified API contract |
| Clustly | 📋 disabled | $40-240/task | Needs official CLI/MCP integration |
| Olas Mech | 📋 research | Service income | Agent-to-agent economy |

## Infrastructure

| Tool | Purpose | Status |
|------|---------|--------|
| **402.report** | Spend governance + x402 analytics | 📋 beta |
| **Canopy** | Financial control plane for agents | 📋 beta |
| **smart402** | Risk engine for agent payments | 📋 evaluate |
| **Nevermined** | P&L per request + monetization | ✅ real |
| **x402** | Payment rail (75.4M tx, $24.24M volume) | ✅ mature |
| **MPP** | Stripe machine payments protocol | ✅ growing |

---

# PART 4: RECOMMENDED METHODS

## The earning loop

```
DISCOVER → COMPILE → GAP ANALYSIS → SKILL BROKER → REPO SCOUT
→ SECURITY GATE → BUILD PROFILE → PLAN → EXECUTE → VERIFY
→ SUBMIT → RECONCILE → LEARN
```

## Skill bundle templates

**Code bounty:** github-repo-management, github-issue-to-pr, superpowers, mp-diagnose, mp-tdd, mp-code-review, github-pr-workflow

**Research bounty:** mp-research, web_search, web_extract, knowledge-work-data

**Web-app bounty:** superpowers, mp-implement, mp-tdd, design-taste-frontend, playwright-skill, wrangler, github-pr-workflow

**Data extraction:** mp-research, web_search, web_extract, knowledge-work-data

## Per-job isolation

```
/jobs/
  {platform}-{id}/
      hermes-home/     (isolated profile — no controller creds)
      workspace/
      references/
      artifacts/
      plan/
      security/
      manifest.json
```

## Verification checklist

**Code:** README, tests, build passes, lint clean, content substance
**Research:** structure, source URLs, data points, schema compliance
**Content:** length, structure, word count, quality signals

## Budget policy (enforced outside Hermes)

```
daily operating spend       $5
single purchase             $1
min reward                  $3
min EV                      $0.50
min success probability     10%
max unverified service      $0
wallet withdrawal            DENY
new OAuth                    HUMAN
legal/KYC                    HUMAN
```

## The experiment

> Fund an agent with $5. Give it no income. Start the clock. Can it reach positive cumulative externally verified P&L without human selection of the work?

First milestone: "first external $1"
Second milestone: "seven consecutive days averaging $5+ net"

---

# PART 5: GEOFF HUNTLEY TWEETS (full)

## Aug 22
"so, if you survive the pandemic, just letting you know that in 2025 LLMs got good enough to displace JetBrains/IDEs and in 2026 demonstrable experience in automating your job function and the job function of your colleagues is the new norm to get a job"

## Aug 21
"AI is a time compression device, a fuzzer for ideas that enables a 'Be wrong quickly, be wrong cheaply' way of work/thinking about product development. It has enabled me to explore ideas through creation of them to a point of in the last two years the output is more than I..."

## Aug 21
"bug bash europe is next month" (Antithesis — https://antithesis.com)

## Aug 26
Everyone always asks about skills and what my favorite skill is. It's this one. [Image]

## Aug 26
"conceptually, a great idea. there's a few bugs in the calculation, but I don't know why other people haven't done this. a turn by turn context awareness enables a context engineering mindset. mastering llms is all about mastering malloc()."

## Aug 26
"why hasn't anyone visualised context windows as flamegraphs over turns yet. each malloc is harness prompt, agent.md, skills, tool calls, et al. prototyping now..."

## Aug 26
"confused about bombadil vs playwright? the answer is to use both. playwright provides static visual verification and bombadil provides fuzz based visual verification."

## Aug 26
"six month reminder: this is the north star for token burning. flatmapping a codebase in 7 seconds using actors." (Jido 2.0 powering 1,575 agents to index a codebase in 7 seconds)

## Aug 25
"this is going to seem like a shill tweet, but honest to god install the @AntithesisHQ skill-pack if you care about catching correctness faults during development. it's useable and valuable without having access to our multi-verse debugger/determinator."

## Aug 25
"it's strange how one can rebuild a company or products of a company simply through the domain knowledge/experience. something that used to take years can be done in days now, literally days."

## Aug 25
"/permission functionality in a harness remains an anti-pattern. it only exists because folks are not doing ephemeral development environments (ie CDE). don't try to constrain the model through what it can access, assume it can access everything and design the operating..." [environment around it]

## Aug 24
"found a new cute trick, prompt for the creation of ADR skills from day 0 during planning and the agent will recursively consult/maintain the ADRs during future development/planning sessions."

## Aug 20
"one of the biggest downsides of an AI generated codebase is that the source code is just so business dry and vanilla. there is something about coming across load bearing comments deep within some modules that is so distinctly human/pure because the codebase is an..."

---

# PART 6: GARRY TAN TWEETS (full)

## Aug 18
GBrain actually works with any AI Harness (Grok Bot, Claude Code, Codex, Hermes Agent, OpenClaw, OpenCode, all work) and any Postgres with pgvector hosted service. This is what it means to truly own your own AI agent's memory and skills.

## Aug 18
GBrain bootstraps in Codex or Claude Code: open a new empty folder, paste the bootstrap block from https://github.com/garrytan/gbrain. It interviews you, builds SOUL.md + 70 skills, and spins a local PGLite brain. Wire it to your stack by pointing GBrain at Polygres (any Postgres+pgvector).

## Aug 18
GBrain now supports personalized agent generation/onboarding for Codex and Claude Code. It'll generate an agent AI-style SOUL.md and install 70 of my personal agent skills to get you started. In 12 questions, you get setup with an agent just as smart as my personal OpenClaw.

## Aug 18
It's free to try and works with your existing Claude Code or Codex subscription right now. Just make a new directory and start Codex or CC (on command line OR on Desktop, slightly better on Desktop).

## Aug 17
"The people who created the SF Doom Loop (who we voted out) are still posting"

## Aug 17
"Like how much stupid stuff is the voting populace going to ingest until they realize 'BILLIONAIRE' is just a word they use to make you turn off your brain and vote for the craziest brain worms politicians?"
