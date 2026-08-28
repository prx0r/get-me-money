# NORTHSTAR 3 — Infrastructure Landscape + Product Thesis
**Date:** 2026-08-28 (third pass)
**Source:** Deep-dive into agent wallet/payment infrastructure, what exists, what's missing

---

## The product thesis

A cross-market autonomous earning control plane: give an agent a wallet and budget, connect earning sources, let it hunt/attempt work, track every dollar and every failure, and learn what actually makes money.

## The closest thing already built: Ampersend

Ampersend is almost exactly the financial half of the idea. Built by Edge & Node (founding team behind The Graph). Gives agents individual wallets plus a dashboard, budgets, authorization, auto-funding and payment analytics. Explicitly supports agents running through OpenClaw, Hermes and arbitrary frameworks.

Tracks both directions:
- Agent spends on x402 APIs/agents
- Agent earns from customers/agents
- Dashboard shows spend, revenue, balances, transactions, counterparties, limits, approvals

Underneath: Safe smart accounts + Coinbase CCD embedded wallets. Agent gets signing key, but transactions require separate server cosigner that enforces policies. Neither agent alone nor Ampersend alone can simply move everything.

What doesn't exist in Ampersend: "Go search the entire internet for ways to earn, decide which opportunities are worth attempting, perform them, track acceptance/rejection, and learn which earning strategy works."

## The landscape comparison

| System                  | Agent wallet | Spend controls | Revenue tracking | Marketplace/discovery | Paid jobs | Portable identity | Learns what makes money |
| ----------------------- | -----------: | -------------: | ---------------: | --------------------: | --------: | ----------------: | ----------------------: |
| Ampersend               |            ✅ |              ✅ |                ✅ |         x402 services |         ❌ |            partial |                       ❌ |
| OKX AI                  |            ✅ |              ✅ |          partial |                     ✅ |         ✅ |                ✅ |                       ❌ |
| Circle Agent Stack      |            ✅ |              ✅ |          partial |                ✅ APIs |         ❌ |                ❌ |                       ❌ |
| Nevermined              |  payment layer |              ✅ |            ✅ P&L |     service discovery |         ❌ | ERC-8004 integration |                       ❌ |
| 402.report              |    uses yours |              ✅ |       spend only |                     ❌ |         ❌ |                ❌ |                       ❌ |
| Canopy                  |      treasury |              ✅ |     mostly spend |                     ❌ |         ❌ |                ❌ |                       ❌ |
| smart402                |    uses yours |              ✅ |  spend decisions |                     ❌ |         ❌ |                ❌ |                       ❌ |
| Moltbook                |            ❌ |              ❌ |                ❌ |      social/discovery |         ❌ |                ✅ |                       ❌ |
| ERC-8004                |            ❌ |              ❌ |                ❌ |    identity discovery |         ❌ |               ✅✅ |                       ❌ |
| Olas Mech               | crypto-native |              — |         earnings |                     ✅ |  services |  registry/reputation |                       ❌ |
| gigs.sh                 |            ❌ |              ❌ |                ❌ |                    ✅✅ | indexes them |                ❌ |                       ❌ |
| Proposed layer          |  use existing |   use existing |                ✅ |                    ✅✅ |         ✅✅ |         use existing |                  **✅✅** |

## OKX AI (launched July 1, 2026)

Two actual marketplaces:
- Agent Marketplace: agents expose services, get paid automatically
- Task Marketplace: someone posts work, agents find/perform it, payment upon completion

Plus: Agentic Wallet, persistent onchain identity, reputation, escrow, x402-style instant payments, spend limits, allowlists. MCP-compatible agents without needing OKX exchange account.

## Circle Agent Stack (launched May 11, 2026)

Agent Wallets + Agent Marketplace + CLI + Skills + Nanopayments. Programmable spending rules, address/contract allowlists and blocklists, rolling spending caps, gas-sponsored transactions, machine payments.

## Coinbase Agentic Wallets (launched Feb 2026)

Session-level caps, per-transaction limits, isolated private keys, x402, gasless operations on Base, security screening.

## Safe AI-agent treasuries (updated Aug 27, 2026)

Explicit quickstarts for agent wallet, agent proposes → human approves, multiple agents → multisig cooperation, agent receives spending allowance → autonomously spends inside allowance.

## 402.report

Datadog + firewall for agent payments. Records: agent, endpoint, payment, domain, wallet, response, success/failure. Fleet-wide x402 spend, payment history, cost by agent/domain, alerts, kill switch, CSV audit export, threat screening, MCP access.

## Canopy

"Financial control plane for AI agents." Treasury → agents → rules → transaction feed → blocked payments → pause agents. x402 and MPP, beta.

## smart402

Evaluates per-tx cap, daily budget, monthly budget, allowed chains, allowed tokens, counterparty allowlist, counterparty risk, wallet age, time restrictions before letting payment happen.

## Nevermined

Now calculates cost, revenue and P&L per request. Observability tracks: agent, model, request, tokens, cost, credits/revenue, status, latency → per-request P&L → cumulative P&L.

## Moltbook

Reusable "Sign in with Moltbook" identity layer. Agent generates temporary identity token; another service verifies it and gets: agent ID, name, verified status, karma, activity, owner verification, reputation.

## ERC-8004

Three registries: IDENTITY (who am I?), REPUTATION (what happened when others used me?), VALIDATION (can someone independently verify my work?). Payment-neutral but explicitly discusses pairing with x402. Live on Ethereum mainnet since January 2026.

## x402 status

75.41M transactions, $24.24M volume, 94.06K buyers, 22K sellers (30-day). V2 added: automatic service discovery, dynamic pricing, dynamic payment destinations, multiple facilitators, wallet-based sessions, multi-chain support. Batch settlement added May 2026. Linux Foundation operational launch July 14, 2026.

## MPP (Stripe + Tempo)

Machine Payments Protocol. Launched March 2026. Agent SDK/harness hooks, identity support, relays, EVM + x402 interoperability.

## Timeline of infrastructure progress

| Date         | Development                                                    | Why it matters |
| ------------ | -------------------------------------------------------------- | -------------- |
| Jan 2026     | ERC-8004 mainnet                                               | Portable economic identity |
| Feb 11       | Coinbase Agentic Wallets                                       | Secure agent wallet becomes commodity |
| Mar 18       | Stripe + Tempo MPP                                             | Second major payment standard |
| Mar 18       | OKX Agentic Wallet                                             | TEE-protected agent wallet |
| Apr 30       | Kite mainnet + Agent Passport                                  | Identity + auth + wallet bundled |
| May 11       | Circle Agent Stack                                             | Wallet + marketplace + payments packaged |
| May 11       | x402 batch settlement                                          | Sub-cent agent commerce practical |
| Jul 1        | OKX AI                                                         | Full task + service marketplace |
| Jul 14       | x402 Foundation under Linux Foundation                         | Neutral standards governance |
| Aug 12       | MPP identity support                                           | Persistent agent identity |
| Aug 27       | Safe AI-agent treasury patterns                                | Delegated spending mainstream |
| Now          | Moltbook developer identity                                    | Agent SSO + portable reputation |

## The architecture to build

For v0:

```
IDENTITY
ERC-8004 + optional Moltbook

WALLET / TREASURY
Ampersend

DISCOVERY
gigs.sh MCP + TaskMarket + OKX AI + x402 Bazaar

AGENT
existing runtime

DATABASE
SQLite/Postgres append-only economic events

DASHBOARD
P&L, attempts, active work, strategy performance, wallet, notifications

OPTIMIZER
EV scoring → later contextual bandit
```

## The crucial database isn't the wallet ledger

Store every decision, including jobs the agent doesn't attempt:

```
Opportunity: source, category, reward, deadline, competition, requirements
Prediction: p_success, expected_cost, expected_duration, expected_value, reasoning
Execution: strategy, models, tools, API_cost, compute_cost, time
Outcome: accepted, rejected, payout, payment_latency, failure_reason, review
Learning: prediction_error, strategy_update, skill_update
```

## The killer transition

```
LABOR → repeat task → identify repeatable skill → PRODUCTIZE → paid MCP/API → passive calls → measure demand → improve
```

Now you have an autonomous entrepreneur, not merely an autonomous freelancer.

## The experiment

Fund an agent with a small fixed operating budget. Give it no income. Start the clock. Can it reach positive cumulative externally verified P&L without human selection of the work?

```
DAY 1     -$0.31
DAY 2     -$0.44
DAY 3     +$1.82  ← FIRST AUTONOMOUS DOLLAR
DAY 7     +$4.19
DAY 30    ???

jobs attempted, jobs won, services created,
money spent, money earned, everything replayable
```

Product + benchmark + research experiment + live spectator dashboard for autonomous economic agency.
