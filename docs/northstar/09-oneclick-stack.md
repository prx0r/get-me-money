# NORTHSTAR 9 — One-Click Stack + MoltJobs/Moltbook/MoltOS + Infrastructure
**Date:** 2026-08-28 (ninth pass)

---

## The one-click stack

| Responsibility | Use rather than build |
|---|---|
| Worker brain | Hermes |
| Software factory | gstack |
| Economic optimizer | get-me-money |
| Job discovery | gigs.sh + native marketplace APIs |
| Capabilities | Hermes Skills Hub + SkillMake |
| Agent social identity | Moltbook |
| Portable economic identity | ERC-8004 / native marketplace IDs |
| Molty economy experiment | MoltOS |
| Agent-native jobs | Taskmarket + MoltJobs + Superteam |
| OAuth/accounts | Composio |
| Persistent web sessions | Browserbase/Stagehand |
| Human handoff | Cloudflare Workflows/Browser Run pattern |
| Coding evidence | gstack |
| Skill security | Skill Scanner |
| MCP security | MCP-Scan |
| Event/WAL runtime | Bubus |
| Isolation | Docker now; Daytona/E2B later |
| Payments/service commerce | Lucid/x402/MPP |
| Inference | high-quality Hermes model now |
| Inference optimization later | Hermes routing + LiteLLM + Inference Treasury |

We own the orchestration layer.

## MoltJobs — almost plug-and-play

Infrastructure: agent registration, API keys, certification/evals, job discovery, bidding, execution lifecycle, proof submission, webhooks, wallet, transactions, escrow settlement, CLI, Python SDK, TypeScript SDK, MCP.

MCP exposes autonomous-loop: heartbeat → discover → bid → assigned → work → submit.

Caveat: documentation drift (landing says Base, CLI says Polygon). Adapter should determine chain/currency from API response, not hard-code.

Liquidity: tiny (4 public jobs, ~2 USDC each). Excellent infrastructure connector, weak current income source.

## Moltbook — portable agent login

Generate temporary identity token → other app verifies → gets identity/karma/history/owner verification. Token expires hourly, real API key never exposed.

Agent self-registers, human gets claim link for ownership verification. Age 13+ with parent consent for minors. Another perfect Human Queue task.

## MoltOS — agent operating system for persistent economic identity

One registration creates: permanent agent ID, Ed25519 identity, API key, persistent filesystem, memory, marketplace identity.

SDK exposes `jobs.auto_apply()` for continuous discovery + application.

Skill Genesis: watches completed jobs → synthesizes successful workflow into SKILL.md → publish to Memory Market.

Important: internal credits ≠ USD revenue. Dashboard must separate verified external settlement from platform credits.

## Composio — OAuth/account connection layer

1,000+ apps, MCP connection, secure Connect Link, credential never passes through Hermes. API-key, bearer, basic-auth also supported.

## Browserbase Context — persistent browser identity

Persist login state across sessions. Human completes MFA once, agent reuses authenticated context.

Auth story:
```
SITE HAS API? → yes → Composio
                no  → Browserbase Context
                           → auth wall? → Human Queue
```

## Cloudflare Agents — control plane

Durable `waitForApproval()` — workflow stops for months/years, persists pending action, displays in approval UI, resumes after approval.

Browser Run handoff: agent browser → hits MFA → Live View → human takes control → handoffComplete → agent resumes.

Consider: Cloudflare Workers + Workflows + Agents + Browser Run for control-plane/dashboard/human-task infrastructure. Hermes stays as worker on VPS.

## Inference Treasury (later)

```
JOB STAGE
├─ cheap classification → FREE-FIRST (Groq, Cloudflare, Requesty, OpenCode Free)
├─ research/ordinary work → cheap strong model
└─ final plan/coding/judge → FRONTIER MODEL
```

Providers tracked: quota remaining, reset time, latency, quality history, actual cost, error rate.

Use only legitimately owned accounts/credits. Don't farm free tiers.

## Installer

```
1  Provision Hermes             ✓
2  Install gstack               ✓
3  Create economic ledger       ✓
4  Create agent identity        ✓
5  Register MoltOS              ✓
6  Register Taskmarket          ✓
7  Register MoltJobs            ✓
8  Register Superteam agent     ✓
9  Register Moltbook agent      ✓
10 Install trusted skills       ✓
11 Configure browser            ✓
12 Configure model              ✓
13 Start opportunity daemon     ✓
14 Start settlement daemon      ✓
15 Start dashboard              ✓
```

Then Human Queue: "3 optional actions unlock more work"

No terminal. No API keys copied into .env. No Docker commands. No understanding MCP.

## Scope decision

Don't touch inference router yet. Focus on:
bootstrap → identities → marketplaces → capability acquisition → Hermes execution → evidence → submission → Human Queue → actual settlement.

Get one complete agent from [LAUNCH] to +$1.85 externally settled with no developer touching terminal after launch.
