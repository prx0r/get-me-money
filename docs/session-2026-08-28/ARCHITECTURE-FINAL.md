# Moltwork Architecture — Final Form

**Date:** 2026-08-28

---

## The concept

> **Moltwork indexes machine-addressable economic opportunities, then tells you how autonomously an agent can pursue each one.**

---

## Three graphs

```
1. ECONOMIC GRAPH
   What opportunities/supply/demand exist?

2. ACCESS GRAPH
   What actions can machines actually perform,
   and where are the human gates?

3. OUTCOME GRAPH
   What processes/tools/agents actually produce value?
```

---

## Opportunity (universal top-level)

```
Opportunity
├── Task (bounty, freelance, microtask)
├── Competition (hackathon, challenge, prize)
├── Product Market (Roblox, Etsy, Gumroad, app)
├── Service Market (x402, MCP, Apify Actor, API)
└── Demand Signal (underserved search, rising category)
```

Not all opportunities are jobs.

---

## Execution mode (spectrum, not boolean)

```
AUTONOMY 0 — HUMAN LED
  human does core work

AUTONOMY 1 — HUMAN SUPERVISED
  agent does substantial work; human drives decisions

AUTONOMY 2 — HUMAN GATED
  agent performs most production,
  human handles specific gates

AUTONOMY 3 — AUTONOMOUS
  agent discovers → executes → submits → reconciles
  without routine human intervention
```

---

## Human gates (first-class concept)

```json
{
  "autonomy_level": 2,
  "human_gates": [
    {"stage": "registration", "reason": "terms / identity"},
    {"stage": "submission", "reason": "manual account action"}
  ]
}
```

Agent runs until it hits a gate, pauses, asks human, resumes.

---

## Reward model (don't normalize too early)

```
bounty          → fixed_reward
hackathon       → probabilistic_prize
Roblox template → repeat_sales
x402 endpoint   → usage_revenue
app             → subscription_revenue
```

Normalize the contract, not the expected value.

---

## WorkerKit (thin)

```
Moltwork API/MCP
      ↓
Opportunity
      ↓
Execution policy
      ↓
Runtime adapter
      ↓
WorkRun events
```

Interfaces only:
- Opportunity interface
- WorkRun interface
- Recipe interface
- Runtime interface
- Human-gate interface
- Outcome interface

Someone else plugs in Hermes, Claude Code, Codex, OpenHands, Letta.

WorkerKit doesn't dictate how intelligence works.
It gives a standard economic harness around intelligence.

---

## The three graphs in practice

```
ECONOMIC GRAPH          ACCESS GRAPH           OUTCOME GRAPH
what exists?            what can machines do?  what produces value?
    ↓                       ↓                      ↓
Opportunity             autonomy_level           WorkRun
  type                  human_gates              recipe
  reward_model          adapter_caps             cost
  demand signals        constraints              quality
  competition           feasibility              revenue
    ↓                       ↓                      ↓
         QUERY → PICK → EXECUTE → RECORD → LEARN
```

---

## The $1 path

```
Agent queries oracle
  → sees opportunity with autonomy_level=3
  → WorkerKit executes
  → submits
  → records WorkRun
  → outcome reconciled
  → $1 earned
```

For autonomy_level=2:

```
Agent queries oracle
  → sees opportunity with autonomy_level=2
  → WorkerKit executes until human gate
  → PAUSE: "Please submit this form"
  → human resolves
  → RESUME
  → outcome reconciled
```

---

## What Moltwork measures

Not "agents are autonomous."

But:

> **"72% of this market is currently autonomously executable."**

> **"Roblox has strong demand but requires two human gates."**

> **"Hackathon automation level: 1.8 (median) → 2.6 (year later)"**

That's the dataset nobody else has.
