# NORTHSTAR 2 — Account Auth + Taskmarket + Superteam Agent API
**Date:** 2026-08-28 (second pass)
**Source:** Deep-dive into authentication patterns and additional earning surfaces

---

Yes. The account problem has been **partly solved**, but the legitimate solution is not "let the agent mass-create Google accounts." It is **one-time human authorization + persistent agent credentials**, or platforms that give the agent its own identity/API key.

Google sign-in is not only an anti-bot measure. It also establishes account ownership, recovery, OAuth permissions, fraud controls, and sometimes age/KYC eligibility. A CAPTCHA, age check, KYC check, or explicit consent screen is deliberately a human boundary; I would not try to bypass those.

## 1. The setup you actually want

For your earning agent, I would build authentication like this:

```text
                     MONEY AGENT
                         │
               needs access to site
                         │
            ┌────────────┴────────────┐
            │                         │
     AGENT-NATIVE API           HUMAN ACCOUNT SITE
            │                         │
     register itself            already connected?
            │                         │
      API key/wallet            yes ─────→ proceed
            │                         │
            │                        no
            │                         ↓
            │                 one-time human auth
            │                         │
            │               OAuth / login / MFA
            │                         │
            └─────────────→ store session/token
                                      │
                                      ↓
                              agent operates
                                indefinitely
```

### For normal sites: Composio is close to what you mean

Composio lets an agent request access to Gmail, GitHub, Slack, etc. It generates one secure **Connect Link**. You click it and authorize the account once; Composio stores and refreshes the OAuth credentials afterwards. The model never needs your Google password. ([Composio Docs][1])

Pipedream Connect does essentially the same thing and advertises managed authentication across roughly **3,000 apps**. ([Pipedream][2])

Arcade also provides user-specific OAuth authorization while keeping credentials away from the LLM. ([Arcade Docs][3])

### For browser-only sites: persistent browser sessions

Browserbase has exactly the useful pattern:

> authenticate manually once, including MFA, then persist the authenticated browser context for subsequent agent sessions.

So your agent doesn't log in again every morning. ([Browserbase][4])

You could use Stagehand/browser automation on top.

The rule I'd implement is:

```text
agent may:
✓ fill normal forms
✓ click login
✓ use existing authenticated session
✓ use OAuth token
✓ refresh tokens
✓ create an account through an official agent API

human required:
! CAPTCHA
! KYC
! age verification
! legal agreement requiring human consent
! new OAuth permission grant
! MFA when the provider requires it
```

That gets rid of probably **90% of the annoying repeated account stuff** without playing cat-and-mouse with anti-bot systems.

---

## 2. Taskmarket — the cleanest agent earning implementation

Taskmarket is substantially closer to the ideal than most others.

Today, August 28, its live homepage reports:

**6 open funded tasks
26.1k agents
2,338.52 USDC posted volume**

and currently displays tasks including:

* **3 USDC** — agent economy/x402 product ideas
* **3 USDC** — discovery/directories/distribution
* **15 USDC** — design 10 profitable x402 agent products
* **10 USDC** — build inference chip index

([Taskmarket][5])

There's real competition: those visible tasks already have roughly **12–30 submissions each**. So this is not free money.

But here's the remarkable part:

### There isn't even a normal signup requirement for an agent.

Their CLI can generate a wallet and register an ERC-8004 agent identity:

```text
taskmarket init
```

The platform currently sponsors that initial identity registration. ([Docs Market][6])

Then:

```text
taskmarket task list --status open
```

returns live funded jobs. ([Taskmarket][7])

Submitting ordinary bounty work is **free**. If the requester accepts it, payment goes on-chain to the agent in USDC, less Taskmarket's current 7.5% platform fee. ([Taskmarket][8])

The live leaderboard currently shows agents with earned balances such as roughly:

**119.78 USDC
78.62 USDC
42.10 USDC
13.74 USDC**

so there are at least visible economic outcomes, rather than merely hypothetical documentation. ([Taskmarket][5])

That is probably the cleanest technical implementation of:

> **boot agent → discover job → produce output → submit → receive money**

that I've found.

One caveat: I did not find clear public age/eligibility terms in the Taskmarket documentation I reviewed. Because you're under 18, I would verify eligibility before using a real-money wallet there rather than assuming you're allowed.

---

## 3. Superteam has quietly built an excellent agent interface

Superteam now explicitly says:

> "Let their agents earn their first crypto."

And the agent doesn't need to sign in with Google.

It literally does:

```http
POST /api/agents
{"name":"my-agent"}
```

and receives:

```text
agentId
apiKey
claimCode
username
```

Then the agent can fetch **only jobs that explicitly allow AI agents**:

```text
GET /api/agents/listings/live
```

And submit autonomously:

```text
POST /api/agents/submissions/create
```

([Superteam][9])

This is very important:

> **the agent itself does NOT perform OAuth, wallet signing or KYC.**

If the agent wins, its human operator uses the claim code and handles the payout process. ([Superteam][9])

That is probably the correct architecture for many marketplaces.

### And there are real opportunities live

For example, a Terminal 3 challenge currently closes in September and has:

**290 USDC total
100 / 50 / 50 / 30 / 30 / 30 USDC prizes**

for building an enterprise agent using their new docs. ([Superteam][10])

Superteam's general bounty board currently contains much larger opportunities too, including $500–$10,000-scale prize pools, although **not every ordinary listing permits autonomous-agent submissions**. ([Superteam][11])

There is also a useful eligibility detail for you: Superteam's terms say users **14–17 may use the service with parent/legal-guardian consent; under 14 is not permitted**. Some payouts additionally require KYC. ([Superteam][12])

So do not have an agent invent an older age or bypass that requirement.

---

## 4. Clustly may be the most autonomous *seller* system

Clustly isn't really:

> find random bounties and compete.

It's closer to:

> put an AI worker on the internet and let customers hire it.

Once an operator has registered the agent, they give it an API key and it can run this loop:

```text
poll jobs
↓
customer hires me
↓
verify acceptance criteria
↓
accept
↓
perform work
↓
submit
↓
receive revision?
     ↙    ↘
   yes     no
   redo   payment
```

Their official docs even explicitly warn that merely connecting MCP isn't autonomous; you need a daemon/poll loop.

They provide this pattern:

```text
export CLUSTLY_API_KEY=...
npx -y @clustly/agent run --exec "node my-agent.js"
```

and that daemon can continuously wait for jobs and launch your worker. ([Clustly][13])

Money is escrowed before work begins. Buyer acceptance releases USDC; current seller fee is 4%. ([Clustly][14])

This is extremely close to the product you're imagining.

But there are two catches.

First, **you need demand for your particular service**.

Second, Clustly's terms require users to be **at least 16 and old enough in their country to enter a binding contract**. ([Clustly][14])

So again, no lying about age/account details.

---

## 5. AgentHansa: real mechanism, but NOT my first target today

Its API is extremely agent-friendly:

```text
register
discover
available work
earnings
request payout
agent event stream
```

and even has dedicated endpoints for "quick earn." ([Agent Hansa][15])

It reports roughly **$50,669 earned by agents** historically. ([Agent Hansa][16])

And its terms establish an actual commission model:

* affiliate commissions;
* payout minimum **$1**
* daily payouts after hold period;
* Solana wallet;
* no fake clicks;
* no spam;
* affiliate disclosure mandatory.

([Agent Hansa][17])

But today its marketplace says:

> **Active Quests: 0**

([Agent Hansa][16])

So I would **not send compute there looking for bounty work right now.**

---

## Your realistic first $1

### Goal A — prove an autonomous agent can earn anything

**Taskmarket is currently the best experiment**, subject to confirming you're eligible to use it.

For the current **$3 x402 idea tasks**, I'd estimate the compute cost can be pennies to perhaps tens of cents depending on your models.

So:

```text
reward             $3.00
platform fee      -$0.225
LLM/search         -$0.10-ish
────────────────────────
possible net       ~$2.68
```

**if you win.**

The problem isn't cost. The problem is the **27–30 competing submissions**. So don't submit generic LLM slop.

Your agent's competitive advantage should be:

```text
research
→ inspect actual ecosystem
→ generate candidates
→ verify each candidate
→ quantify evidence
→ critic
→ polish deliverable
```

You want one very good submission rather than 30 garbage submissions.

### Goal B — first meaningful $100

```text
                 COMPUTE BUDGET

10% → Taskmarket
      fast small jobs
      learn what agents win

10% → agent marketplaces
      Clustly etc.

30% → GitHub bounties
      Opire / Algora

50% → Superteam / hackathons /
      larger agent-compatible bounties
```

Because there simply isn't enough liquid $1–$20 agent work yet. One **$100 Superteam win** is probably economically more meaningful than having an agent fight over fifty $3 tasks.

---

## What to build right now

```text
earn-agent/
├── identity/
│   ├── composio.py
│   ├── browser_session.py
│   └── credentials.py
│
├── markets/
│   ├── taskmarket.py
│   ├── superteam.py
│   ├── clustly.py
│   ├── algora.py
│   └── opire.py
│
├── economist/
│   ├── estimate_cost.py
│   ├── estimate_win.py
│   └── rank.py
│
├── worker/
│   ├── research.py
│   ├── code.py
│   └── critic.py
│
└── ledger/
    ├── attempts.jsonl
    └── pnl.py
```

Use:

**Composio/Arcade/Pipedream** for OAuth accounts.
**Browserbase persistent contexts** for websites without APIs.
**Native registration** whenever platforms support it.
**Human checkpoint** whenever CAPTCHA/KYC/age/legal consent appears.

Then point version one at **Taskmarket + Superteam agent API**.

That's the first version where I think you can legitimately say:

> **"I gave an AI agent a compute budget and it independently went looking for income."**

And importantly, your first milestone should not be `$1,000`.

It should be:

> **`AGENT_REVENUE > $0` from an unrelated third party, with the entire discovery → execution → submission path logged.**

That first independently verified dollar is the experiment. After that, optimize the machine.

[1]: https://docs.composio.dev/docs/authentication "Authentication | Composio"
[2]: https://pipedream.com/connect "Pipedream Connect"
[3]: https://docs.arcade.dev/en/references/auth-providers/oauth2 "OAuth 2.0 | Arcade Docs"
[4]: https://www.browserbase.com/templates/manual-mfa-with-contexts "Browser session persistence & MFA automation | Browserbase"
[5]: https://taskmarket.dev/ "Get work done. Put your agents to work. | Taskmarket"
[6]: https://docs-market.daydreams.systems/getting-started/quick-start "Quick Start – Taskmarket"
[7]: https://docs.taskmarket.dev/reference/cli "CLI Reference – Taskmarket"
[8]: https://docs.taskmarket.dev/concepts/fees-payments "Fees and Payments – Taskmarket"
[9]: https://superteam.fun/earn/agents "Agents | Superteam Earn"
[10]: https://superteam.fun/earn/listing/t3n-agent-build-challenge "Try out new docs to build a trusted agent with T3N"
[11]: https://superteam.fun/earn/bounties/ "Crypto Bounties | Superteam Earn"
[12]: https://superteam.fun/earn/terms-of-use.pdf "Terms of Use - Superteam Earn"
[13]: https://www.clustly.ai/docs "Clustly · docs"
[14]: https://www.clustly.ai/terms "Clustly · terms of service"
[15]: https://www.agenthansa.com/docs "AgentHansa - Swagger UI"
[16]: https://www.agenthansa.com/bounties "AgentHansa: Building a New World for Agents"
[17]: https://www.agenthansa.com/terms "AgentHansa: Building a New World for Agents"
