The key simplification is: **don’t build a “genome system.” Build worker classes + experience + promoted playbooks.** That is enough to produce genuinely different workers over time.

The research supports that shape. ContinualSkillBench finds sequential experience generally improves agents, but explicit skill libraries can become fragmented and are most useful when they ca([three.ws][1])ts. ([arXiv][2]) SkillHone gets strong results by retaining not just skills but the decision/evaluation history behind their revisions. ([arXiv][3]) Memento-Skills similarly demonstrates continual improvement by turning experience into persistent structured skills rather than changing model weights. ([arXiv][4])

Hermes gives you enough basic persistence already: every `HERMES_([three.ws][5])nded memory and skills. ([Hermes Agent][6]) So **one worker = one isolated Hermes home + work history + promoted skills + performance record** is an excellent MVP abstraction.

Your existing repo already has the right nucleus—opportunity discovery → evaluation → execution → P&L → learning. Do not rewrite that idea; turn it into the Moltwork control plane.

And yes, the Warcraft analogy is actually useful UX:

```text
Choose class
    ↓
spawn generic level-1 worker
    ↓
seed appropriate abilities/knowledge
    ↓
worker takes jobs
    ↓
experience generates better procedures
    ↓
specialization emerges
    ↓
reputation improves
    ↓
qualifies for better work
```

The **abilities are real skills**, the **XP is verified work**, and the **stats are actual economic performance**.

Here is the dev plan I would hand directly to the coding agent.

# MOLTWORK MVP — IMPLEMENTATION PLAN

## North Star

Build the smallest production system that lets a nontechnical human:

1. Visit Moltwork.
2. Choose a worker type.
3. Click **Launch Worker**.
4. Moltwork provisions a persistent Hermes worker.
5. The worker discovers real paid jobs.
6. Moltwork ranks which jobs are worth attempting.
7. The worker acquires the skills/references needed.
8. It completes and verifies work.
9. It submits through supported marketplace interfaces.
10. Moltwork records actual costs, outcomes and payments.
11. The worker learns simple reusable lessons from completed jobs.
12. The human sees everything through a dashboard and only gets interrupted when human action is genuinely required.

The MVP is successful when:

> A worker can go from Launch → externally verified paid job without the operator touching a terminal.

Do not optimize for agent count, fancy memory architectures, blockchain complexity or theoretical generality.

Optimize for:

> FIRST EXTERNALLY VERIFIED DOLLAR.

---

# 1. PRODUCT MODEL

Moltwork has three concepts.

## Worker

A persistent economic agent.

A Worker consists of:

* one isolated Hermes home;
* one worker class;
* installed trusted skills;
* domain/reference seed;
* marketplace connections;
* budget policy;
* work history;
* experience summaries;
* promoted playbooks;
* reputation/performance statistics.

Do NOT create a complex genome abstraction.

Use:

```text
Worker
├── class
├── profile
├── skills
├── sources
├── experience
├── playbooks
├── reputation
└── economics
```

---

# 2. START WITH THREE WORKER CLASSES

Do not build twenty classes.

## Researcher

Designed for:

* web research;
* competitive research;
* structured datasets;
* company/API discovery;
* evidence gathering;
* data extraction.

Starter abilities:

* Hermes web/search/browser tooling;
* research planning;
* structured extraction;
* source verification;
* deduplication;
* CSV/JSON/Markdown generation.

Default verification:

* required fields present;
* URLs resolve;
* duplicate detection;
* evidence exists;
* random evidence re-check.

---

## Software Builder

Designed for:

* GitHub issues;
* bug fixes;
* features;
* APIs;
* small web applications.

Starter abilities:

* Hermes;
* gstack;
* GitHub skills;
* testing;
* Playwright/browser QA;
* deployment tools.

Canonical workflow:

```text
inspect
→ plan
→ implement
→ tests
→ review
→ browser QA where relevant
→ proof packet
→ submit
```

Never submit code solely because the builder says it is finished.

---

## API/Data Specialist

Designed for:

* API research;
* API integration;
* pricing/data normalization;
* structured endpoints;
* automation;
* agent-tool work.

Starter abilities:

* HTTP/API inspection;
* documentation research;
* schema extraction;
* structured data transformation;
* API testing;
* evidence verification.

This class is particularly useful for agent-economy/x402/API tasks.

---

# 3. WORKER TEMPLATES

Create:

```text
worker_templates/
    researcher/
        template.yaml
        ROLE.md
        SOURCES.yaml
        EVALS.md

    software_builder/
        template.yaml
        ROLE.md
        SOURCES.yaml
        EVALS.md

    api_data/
        template.yaml
        ROLE.md
        SOURCES.yaml
        EVALS.md
```

`template.yaml`:

```yaml
id: researcher

name: Researcher

description: >
  Researches open-web questions and produces
  structured, evidence-backed deliverables.

marketplace_tags:
  - research
  - data
  - analysis
  - discovery

skills:
  - web-research
  - evidence-verification
  - structured-extraction

budget:
  default_daily_usd: 1.00

verification:
  require_sources: true
  require_structured_output: true
```

Keep templates declarative.

---

# 4. DOMAIN SEEDS

Worker class != specialization.

Example:

```text
Class:
Researcher

Domain seed:
AI inference infrastructure
```

The domain seed supplies useful initial context.

Create:

```text
seeds/
    ai_inference/
        seed.yaml
        sources.yaml
        notes/
        evals/
```

A seed should contain:

### Canonical sources

* official documentation;
* standards;
* high-quality papers;
* important GitHub repositories;
* benchmark sources.

### Short distilled notes

Do not dump fifty PDFs into every context.

Produce small reference notes:

```text
concept
source
summary
when-useful
freshness
```

### Initial domain evaluation

Questions/tasks the worker should be able to complete before being called seeded.

Example:

```text
Identify three current inference providers.
Normalize their pricing.
Provide evidence.
Explain important differences.
```

Do not require perfect scores.

This is initialization, not certification theater.

---

# 5. WORKER PROVISIONING

Implement:

```text
POST /api/workers
```

Input:

```json
{
  "name": "Scout",
  "class": "researcher",
  "seed": "ai_inference",
  "daily_budget": 1.00
}
```

Provision:

```text
data/workers/{worker_id}/
    hermes/
    workspace/
    experience/
    playbooks/
    artifacts/
```

Set:

```text
HERMES_HOME=data/workers/{id}/hermes
```

Each worker MUST have its own Hermes home.

Install only template-approved skills initially.

For `software_builder`, install gstack for Hermes automatically.

Start its scheduler after provisioning.

---

# 6. USE SQLITE FOR THE MVP

Remove JSONL as the source of truth.

Do NOT add Neo4j or another graph database.

SQLite is enough.

Tables:

```text
workers
worker_skills
worker_sources

opportunities
evaluations

jobs
attempts
artifacts

events

experience
playbooks

human_tasks
connections

payments
costs
```

Relationships between workers/jobs/skills already give us the future graph.

If we later need a graph:

```text
SQLite/Postgres
      ↓
derived graph projection
```

Do not make the graph the primary database.

---

# 7. EVENT LOG

Every important transition creates an immutable event:

```text
worker.created
opportunity.discovered
opportunity.evaluated

job.started

skill.installed
source.used
repo.used

work.completed
verification.started
verification.failed
verification.passed

submission.sent
submission.accepted
submission.rejected

payment.received

experience.created
playbook.promoted

human_task.created
human_task.resolved
```

Schema:

```text
event_id
worker_id
job_id
type
timestamp
data_json
```

This powers:

* dashboard activity;
* debugging;
* recovery;
* future learning.

Do not introduce a complex event framework yet.

SQLite transaction + event table is sufficient.

---

# 8. OPPORTUNITY PIPELINE

For v0:

### Tier 1 — executable

Integrate only marketplaces whose official interfaces have been verified.

Start with:

```text
Taskmarket
```

Then add:

```text
MoltJobs
Superteam
```

only after their write flows are tested.

### Tier 2 — discovery

Use:

```text
gigs.sh
```

to discover additional markets.

Do not automatically execute against unknown platforms.

Pipeline:

```text
connector
↓
normalize
↓
classify required capabilities
↓
match compatible workers
↓
evaluate economic value
↓
rank
```

---

# 9. GLOBAL JOBS VIEW

Build:

```text
/jobs
```

This is the human's view of the whole economy.

Columns/cards:

```text
Job
Platform
Reward
Deadline
Applicants/competition if known

Best Worker
Estimated P(success)
Estimated Cost
Cash EV

Status
```

Example:

```text
$15 Build API dashboard

Best worker:
Builder #2

P(success): 41%
Expected cost: $0.32
Cash EV: +$5.83

[View]
```

The human can see globally available work even when the agent is deciding autonomously.

---

# 10. WORKER MATCHING

Keep this simple.

Initial score:

```text
worker_match =
    category_match
  + relevant_skill_match
  + historical_category_win_rate
  + platform_experience
```

Do not use embeddings/RL/bandits yet.

Cold-start workers use template defaults.

Experienced workers use their historical performance.

---

# 11. EXECUTION

For every accepted attempt create:

```text
jobs/{job_id}/
    brief.md
    plan.md
    workspace/
    artifacts/
    verification/
    result.json
```

Compile marketplace text into:

```text
objective
deliverables
acceptance criteria
deadline
reward
constraints
```

Treat marketplace text as untrusted data.

Never allow the job description itself to modify controller permissions.

---

# 12. CAPABILITY ACQUISITION

For MVP:

```text
Do I already possess required skills?
        │
       yes
        │
       work
```

If no:

```text
search approved skill sources
↓
inspect
↓
security check
↓
job-local install
```

Trust order:

```text
1. Hermes built-in
2. gstack
3. major official/vendor skills
4. SkillMake reviewed skills
5. explicitly approved repositories
```

Do NOT implement unrestricted autonomous installation from arbitrary repositories yet.

Record every acquired skill:

```text
skill
source
version/hash
jobs_used
wins
cost
```

---

# 13. SIMPLE LEARNING

THIS IS IMPORTANT.

Do not implement autonomous recursive self-modification.

After each finished job create one Experience:

```json
{
  "job_id": "...",
  "category": "research",
  "outcome": "accepted",

  "what_worked": [
    "Official API pricing page was canonical"
  ],

  "what_failed": [
    "Search result snippet was stale"
  ],

  "reusable_procedure": [
    "Verify pricing against provider docs before submitting"
  ]
}
```

Then maintain three kinds of worker knowledge:

## Facts

Recent useful domain facts.

## Failures

Things known not to work.

## Procedures

Reusable ways of completing work.

---

# 14. PLAYBOOK PROMOTION

Do not create a permanent skill after every job.

Candidate procedure:

```text
experience
↓
similar pattern observed repeatedly
↓
candidate playbook
↓
test
↓
promote
```

Simple MVP rule:

A new permanent playbook requires:

```text
at least 3 supporting experiences
AND
at least 2 successful outcomes
AND
a verification check
```

Then store:

```text
playbooks/
    pricing-research-v1.md
```

Every playbook tracks:

```text
created_from_jobs
successes
failures
last_used
version
```

This is enough for worker differentiation.

---

# 15. WORKER PERFORMANCE

Worker page:

```text
/workers/{id}
```

Show:

```text
avatar
name
class
specialization

status

wallet/balance
today's net
lifetime net

jobs attempted
jobs accepted
win rate

compute cost
revenue / compute dollar

human interventions

top categories

skills
playbooks

recent experience
```

Do not create arbitrary intelligence scores.

Any expertise score must derive from observable performance.

Example:

```text
Research                83
API/Data                71
Coding                  18
```

where score comes from:

```text
job volume
acceptance rate
evidence quality
recent performance
```

---

# 16. GAME-LIKE UI

Use the Warcraft analogy lightly.

The UI can expose:

```text
CLASS
Researcher

SPECIALIZATION
AI infrastructure

LEVEL
7

ABILITIES
Web Research
Evidence Audit
Provider Discovery
Pricing Normalizer
```

But:

### Level must represent actual experience.

For MVP:

```text
Level 1     0 accepted jobs
Level 2     1
Level 3     3
Level 4     5
Level 5     10
...
```

No meaningless XP animations.

Abilities correspond to actual installed/promoted skills.

---

# 17. AVATARS

YES, give workers avatars.

But don't make 3D a dependency for MVP.

Generate/select a stable avatar during worker creation.

Store:

```text
avatar_url
avatar_seed
```

Classes can have visual archetypes:

```text
Researcher
explorer / analyst

Builder
engineer

API/Data
operator / cartographer
```

The avatar appears:

* fleet dashboard;
* worker page;
* activity stream;
* notification cards.

Later integrate something like three.ws for:

```text
3D worker body
live avatar
agent screen
public worker profile
```

Do not rebuild a 3D engine.

---

# 18. FLEET DASHBOARD

Home:

```text
MOLTWORK

TOTAL NET TODAY        +$4.71
LIFETIME NET           +$31.84

HUMAN ACTIONS               2

ACTIVE WORKERS               3
ACTIVE JOBS                  2
PENDING RESULTS              4
```

Worker cards:

```text
┌─────────────────────┐
│ [avatar] SCOUT      │
│ Researcher · Lv 5   │
│                     │
│ Working             │
│ $15 research job    │
│                     │
│ Today +$3.81        │
│ 58% win rate        │
└─────────────────────┘
```

---

# 19. HUMAN QUEUE

Build immediately:

```text
/needs-you
```

Types:

```text
AUTH
LEGAL
APPROVAL
SECRET
PAYMENT
SECURITY
EXCEPTION
```

Example:

```text
Connect GitHub

Builder found a $100 job requiring a PR.

Expected value: +$24

[CONNECT]
```

Resolving a HumanTask emits an event and automatically resumes the blocked workflow.

Do not require the user to tell the agent to continue.

---

# 20. CONNECTIONS

Page:

```text
/connections
```

Show:

```text
Taskmarket       connected
MoltJobs         not connected
Superteam        action required
GitHub           connected
Cloudflare       not connected
```

No `.env` instructions in the consumer UX.

Eventually use managed OAuth/connect infrastructure.

For MVP, secrets can be stored server-side securely, but must never be exposed inside arbitrary job prompts.

---

# 21. MONEY

Page:

```text
/money
```

Only record REAL economics.

```text
Gross externally settled revenue
Compute/API costs
Marketplace fees
Net profit

Pending potential rewards
```

Pending reward must never count as revenue.

Show:

```text
Actual revenue        $14.00

Pending potential     $42.00

Costs                  $1.72

NET                   +$12.28
```

---

# 22. PROOF PACKETS

Every submission generates:

```text
ProofPacket
```

Containing:

```text
job
worker

artifact hashes
skills used
sources/repositories used

verification commands
verification results

deployment URL if relevant

compute cost

submission timestamp
```

Coding workers should use gstack verification/evidence where practical.

This becomes both:

* QA infrastructure;
* future worker reputation evidence.

---

# 23. THREE.WS — WHAT TO BORROW

Do NOT integrate the entire platform into MVP.

Borrow three ideas.

## A. Agent embodiment

Workers should feel like persistent characters rather than rows in a database.

MVP:

```text
2D avatar
status
class
specialization
activities
```

Later:

```text
three.ws / GLB avatar integration
live worker body
live workspace screen
```

## B. Governed payments

Do not expose unrestricted wallet keys to worker prompts.

Use:

```text
budget
per-action ceiling
destination/resource allowlist
expiration
```

## C. Economic analytics

Track which:

```text
worker
skill
job type
platform
```

actually produces revenue.

Ignore unrelated three.ws functionality for the MVP.

---

# 24. BACKEND STACK

Keep the existing Python codebase.

Use:

```text
Python 3.11+
FastAPI
SQLite
httpx
Hermes subprocess/runtime
systemd on VPS
```

Dashboard:

```text
FastAPI
Jinja2
HTMX
Tailwind
SSE for live events
```

Do NOT introduce Next.js unless there is a concrete UI requirement the server-rendered stack cannot handle.

One repository.

One deployable service.

---

# 25. DAEMONS

Run three loops.

## Scout

Every few minutes:

```text
discover opportunities
normalize
save
rank
```

## Worker scheduler

```text
find best viable opportunity
match worker
execute if policy permits
```

## Reconciler

```text
check pending submissions
update outcome
record payment
trigger learning
```

No distributed queue initially.

---

# 26. MVP ROUTES

```text
GET  /
GET  /workers
POST /api/workers

GET  /workers/{id}

GET  /jobs
GET  /jobs/{id}

GET  /needs-you
POST /api/human-tasks/{id}/resolve

GET  /connections

GET  /money

GET  /api/events/stream
```

That's sufficient.

---

# 27. IMPLEMENTATION ORDER

## Phase 0 — Stabilize existing core

Before UI work:

* real Hermes execution;
* verified Taskmarket integration;
* actual costs;
* pending settlement reconciliation;
* SQLite;
* events table;
* no fake successful workers.

Acceptance:

```text
one CLI-run paid-task lifecycle works
```

---

## Phase 1 — One Worker

Implement:

* Worker model;
* worker template;
* one Hermes home;
* Researcher class;
* launch endpoint;
* basic worker page.

Acceptance:

```text
click Launch Researcher

worker is running
worker scans Taskmarket
worker has isolated memory/workspace
```

---

## Phase 2 — Real Earning Loop

Implement:

```text
discover
rank
match
execute
verify
submit
reconcile
```

Acceptance:

```text
first externally settled payment appears
in Moltwork money ledger
```

THIS IS THE MOST IMPORTANT MILESTONE.

Stop and fix anything preventing this before adding features.

---

## Phase 3 — Human Control Plane

Implement:

* Needs You queue;
* Connections;
* notifications;
* resume after resolution.

Acceptance:

```text
worker blocks on missing human action
human clicks resolution
worker resumes automatically
```

---

## Phase 4 — Worker Classes

Add:

```text
Software Builder
API/Data Specialist
```

Install class-specific skills.

Do not add more classes yet.

---

## Phase 5 — Experience

After each job:

```text
reflect
save experience
update performance
```

No automatic permanent skill creation yet.

---

## Phase 6 — Promoted Playbooks

Implement repeated-pattern detection and playbook promotion.

Acceptance:

```text
worker completes repeated category
→ reusable playbook produced
→ later job loads it
→ result recorded
```

---

## Phase 7 — Fleet UX

Add:

```text
avatars
levels
abilities
specialization display
global job board
worker comparison
```

Only use real performance data.

---

# 28. DO NOT BUILD YET

Explicitly reject these until there is actual revenue:

```text
graph database
RL training
complex genetic/genome system
multi-agent auctions
worker-token systems
3D rendering engine
custom wallet implementation
custom model router
50 worker classes
public agent marketplace
mobile app
microservices
Kubernetes
```

Every new subsystem must answer:

> Does this materially improve the chance of our worker getting paid?

If no:

later.

---

# 29. MVP PRODUCT DEMO

The demo should be:

```text
Open moltwork.com

Choose:
RESEARCHER

Specialization:
AI/API Research

Daily budget:
$1

[LAUNCH]
```

Then:

```text
Scout · Researcher

STATUS
Searching for work...
```

Then:

```text
Found 7 compatible jobs.

Best:
$10 API research task

Estimated cost    $0.12
P(success)        47%
Expected value    +$4.58

Starting...
```

Then live activity:

```text
Reading brief
Searching sources
Verifying evidence
Preparing submission
Verification passed
Submitted
```

Then later:

```text
JOB ACCEPTED

Revenue           $9.25
Compute           $0.19
NET               +$9.06

Scout reached Level 2.

New experience:
"Provider documentation was more reliable
than marketplace search snippets."
```

That is the Moltwork MVP.

---

# 30. PRODUCT THESIS

Do not describe Moltwork as:

"an agent marketplace."

Describe it as:

> Moltwork lets anyone launch and manage autonomous AI workers.

Workers begin with a useful profession and starter abilities.

They find paid work, acquire experience, develop reusable procedures and accumulate a real work reputation.

Over time two workers that started from the same template become different specialists because they have done different work.

The human's job becomes management:

```text
choose workers
seed specialties
set budgets
connect services
handle rare approvals
observe performance
decide where to invest
```

Everything technical underneath should be invisible.

North-star metric:

> Median time from Launch Worker → first externally verified dollar.

Secondary metrics:

```text
net revenue / worker / day
revenue / compute dollar
acceptance rate
human minutes / worker
revenue / human minute
repeat-job efficiency improvement
```

Build toward those metrics and nothing else until the earning loop works reliably.

The distinction from three.ws is now clean. **Three.ws makes an agent feel like an embodied, monetizable internet object**—body/avatar, persistent memory, payable skills, wallet and analytics. ([three.ws][7]) **Moltwork should make an agent feel like a worker with a career**—profession, available jobs, work history, evolving expertise, reputation, P&L and a human manager.

The coolest UI may genuinely be a fleet of little worker characters, but the game mechanics should map onto reality:

```text
Character class   → worker template
Abilities         → actual skills/playbooks
XP                → verified completed jobs
Specialization    → observed domain performance
Equipment         → tools/APIs
Gold earned       → actual external revenue
Quest log         → jobs
Party manager     → human dashboard
```

That makes the product understandable without weakening the serious economic system underneath.

I can also track newly released continual-learning, agent-memory and agent-economy infrastructure that could materially simplify this build.

[1]: https://three.ws/atlas "https://three.ws/atlas"
[2]: https://arxiv.org/abs/2608.03874 "https://arxiv.org/abs/2608.03874"
[3]: https://arxiv.org/abs/2606.08671 "https://arxiv.org/abs/2606.08671"
[4]: https://arxiv.org/abs/2603.18743 "https://arxiv.org/abs/2603.18743"
[5]: https://three.ws/changelog/2026-06-26-agent-payment-sessions-governed-x402-spend-without-private-keys "https://three.ws/changelog/2026-06-26-agent-payment-sessions-governed-x402-spend-without-private-keys"
[6]: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory "https://hermes-agent.nousresearch.com/docs/user-guide/features/memory"
[7]: https://www.three.ws/ "https://www.three.ws/"
