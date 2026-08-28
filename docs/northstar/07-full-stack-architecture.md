# NORTHSTAR 7 — Full Stack Architecture + High-Signal Repos
**Date:** 2026-08-28 (seventh pass)
**Source:** Deep analysis of high-signal repos for transplanting into get-me-money

---

## The frontier stack

| Repo | What to steal | Priority |
|------|--------------|----------|
| garrytan/gstack | /autoplan → build → review → qa → ship, evidence ledger, hostile issue-text guard | S |
| browser-use/bubus | Typed event bus + WAL + replay + concurrency control | S |
| cisco-ai-defense/skill-scanner | Static + YARA + dependency + LLM + dataflow scanning | S |
| invariantlabs-ai/mcp-scan | Runtime MCP proxy, tool pinning, prompt-injection filtering | S |
| browser-use/browser-harness | Self-improving CDP browser + per-domain learned helpers | S |
| browserbase/stagehand | AI exploration → cached deterministic browser workflow | S |
| daydreamsai/skills-market | Commerce-oriented skills + skill-design rules | S |
| daydreamsai/lucid-agents | x402/MPP/A2A/ERC-8004, policy, idempotency, accounting | S |
| SWE-agent/mini-swe-agent | Minimal issue→patch agent, >74% SWE-bench | A |
| daytonaio/daytona | Fast isolated agent computers | A |
| e2b-dev/E2B | Cloud agent sandboxes | A |
| microsoft/agent-lightning | RL/prompt optimization over arbitrary agents | A later |
| anthropics/skills | Production Agent Skills patterns | A |
| modelcontextprotocol/registry | Official MCP discovery | A |
| erc-8004/erc-8004-contracts | Portable identity + reputation | A |
| x402-foundation/x402 | Official payment protocol | A |
| coinbase/agentkit | Wallet abstraction + capped x402 | B |
| nevermined-io/payments | Seller registration, paid agents, A2A | B |
| nirholas/three.ws | Spend reservation, kill switch, revenue ledgers | B reference |
| OpenHands/OpenHands | Scalable remote coding-agent workspaces | C |
| openai/openai-agents-python | Trace/span schema, guardrail primitives | C reference |

## Key insights from each

### gstack
- Evidence ledger: what verification ran against which worktree hash
- Issue guard: identifies injection in bounty descriptions
- Domain browser skills: per-domain knowledge that becomes trusted after success
- Already supports Hermes: `./setup --host hermes`

### bubus
- Replace JSONL spaghetti with typed events + WAL
- Every action has parent_event_id for job attribution
- Crash recovery via WAL replay

### skill-scanner + mcp-scan
- Skills: static + YARA + dependency + LLM semantic scanning
- MCP: tool pinning via hashes, detects rug pulls
- Pipeline: search → download → scan → quarantine → install

### browser-harness + stagehand
- Harness: explore unknown sites, agent writes helpers for itself
- Stagehand: successful AI actions become cached deterministic workflows
- Loop: expensive AI → worked 3 times → cheap cached → site changes? → AI repairs

### lucid-agents
- Protocol-agnostic commerce: x402, MPP, A2A, ERC-8004
- Owns policy, idempotency, fulfillment, discovery, accounting
- Don't build payment layer — use this

### mini-swe-agent
- 100 lines, >74% SWE-bench
- Use as second opinion or fallback for high-value code bounties

### agent-lightning
- RL/prompt optimization over arbitrary agents
- Reward signal: actual_payment - actual_cost
- Collect trajectories now, train later

## Architecture

```
EARNBOX
  → OPPORTUNITY SCOUT
  → JobTextGuard [gstack]
  → JOB COMPILER
  → ECONOMIC ENGINE (get-me-money)
  → CAPABILITY BROKER
  → Skill Scanner + MCP Scan
  → JOB SANDBOX (Daytona/Docker)
  → HERMES + GSTACK
  → Browser Harness / Stagehand
  → VERIFY GATE (gstack evidence)
  → PROOF PACKET
  → SUBMIT
  → PAYMENT/OUTCOME
  → BUBUS event ledger
  → DASHBOARD + MEMORY
  → Agent Lightning (eventually)
```

## Implementation order

1. Install gstack for Hermes + ProofPacket model
2. Replace lifecycle JSONL with Bubus events + WAL
3. CapabilityBroker v1 with Cisco Skill Scanner
4. Browser Harness → Stagehand crystallization loop
5. Lucid Agents for commerce
6. Record trajectories for Agent Lightning
