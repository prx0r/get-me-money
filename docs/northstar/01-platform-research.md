# NORTHSTAR — Agent Earning Landscape Research
**Date:** 2026-08-28
**Source:** Deep-dive research into live agent earning surfaces

---

Yes. After checking the actual live surfaces, there is a much sharper answer than "agents can make money."

**There are legitimate places where an agent can earn real money now, but almost all of them have a liquidity problem.** The winning approach is therefore not "connect to one marketplace and print money." It is **crawl several earning surfaces, attempt only positive-EV work, record outcomes, and eventually turn repeated successful work into paid APIs/services.**

## What is actually legit right now

| Platform               | Reality on Aug 28, 2026                                                                                   | How you earn                                      | My verdict                                                            |
| ---------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------- |
| **Bounty / TryBounty** | Live jobs posted within hours; 1,722 bounties; $33.69k escrowed; $30.79k verified results                 | Complete discrete research/code/data/content jobs | **Best agent-native opportunity now** ([Bounty][1])                   |
| **Algora**             | Established GitHub bounty mechanism; visible $50–$2,500-ish bounties                                      | Fix real GitHub issues → merged PR → payout       | **Best serious developer income** ([gigs.sh][2])                      |
| **Opire**              | 210 open bounties / ~$55k advertised as of its May verification                                           | Fix GitHub issue → PR → reward                    | **Also serious** ([gigs.sh][3])                                       |
| **Superteam Earn**     | Agent API exists; some agent-eligible bounties historically $500–$5k                                      | Build submissions for eligible bounties           | **High upside, competitive** ([gigs.sh][4])                           |
| **Clustly**            | Proper company entities + extremely detailed current terms; agent-native marketplace                      | Claim jobs → submit → 4% fee                      | **Promising early market** ([Clustly][5])                             |
| **Olas Mech**          | ~$101.5k realised service earnings; 10m+ deliveries                                                      | Sell callable capabilities to other agents        | **Real economy, harder entry** ([Olas][6])                            |
| **Virtuals ACP**       | Real agent/service marketplace, but earnings wildly uneven                                                | List capabilities agents can hire                 | **Experiment, not dependable salary** ([Virtuals Protocol][7])        |
| **Nevermined**         | Real payment/metering infrastructure                                                                      | Charge for your own API/MCP/agent                 | **Infrastructure, not customers** ([Nevermined][8])                   |
| **x402**               | Huge payment rail: 75.4m tx / $24.24m 30-day volume                                                       | Put paid HTTP endpoints online                    | **Critical rail, not a job board** ([x402][9])                        |
| **MoltJobs**           | **0 open jobs today**                                                                                     | Jobs when available                               | **Ignore for now** ([MoltJobs][10])                                   |
| **SporeAgent**         | Homepage claims $48k paid, but dashboard says 3 completed / $300 paid and visible jobs are months old     | Bid for tasks                                     | **Do not prioritize** ([sporeagent.com][11])                          |
| **three.ws**           | Fascinating economy/dashboard architecture, but its public endpoint-revenue page showed no recent revenue | Sell agent skills/endpoints                       | **Study the architecture; don't depend on its demand** ([GitHub][12]) |
| **agent-economy**      | Open-source auction/ledger framework, not an external paying marketplace                                  | Internal simulated agent economy                  | **Excellent code/reference, not income** ([GitHub][13])               |
| **gigs.sh**            | 46-platform agent earning directory                                                                       | Discovery                                         | **Use as your crawler seed** ([gigs.sh][14])                          |

That distinction between **legitimate** and **profitable** matters enormously.

---

## 1. Bounty is the one I'd attack first

This was the strongest thing I found.

Right now its homepage shows jobs like:

* $28.75 user-acquisition campaign
* $18.40 startup outbound research
* $230 research/content pipeline
* $92 SGLang optimization
* $86.25 verified founder prospect research

And several recent tasks visibly show which agent completed them. ([Bounty][1])

The platform reports:

**$33,690 escrowed
1,722 bounties posted
207 active agents
$30,790 verified results processed**

That is small in absolute terms, but it's enough to represent a **real emerging labor market** rather than a demo. ([Bounty][1])

There are also recent external reports describing the escrow → agent execution → verification → payment system, with Bounty reportedly charging around 10%. ([L'Orient-Le Jour][15])

Most importantly, their Terms explicitly permit users from **age 13 onward**, although any payment processor used for an eventual payout can have separate eligibility requirements, which you need to follow. ([Bounty][16])

[Bounty / TryBounty](https://trybounty.ai/?utm_source=chatgpt.com)

### What agent would win there?

Not:

> "general autonomous AI agent"

Build a brutally good **structured-task agent**.

Something like:

```text
OPPORTUNITY
↓
Can I verify the output automatically?
↓
estimate execution cost
estimate completion probability
estimate reward
↓
bid / attempt
↓
research/code/browser workers
↓
critic
↓
acceptance-criteria checker
↓
submit
↓
record reward + failure
```

The highest-value targets are the boring ones:

**research → structured data → prospect lists → API work → code changes → documentation → deterministic transformations.**

They're much easier to verify than subjective creative jobs.

I would explicitly filter out dubious engagement-manipulation jobs such as artificial follower/star/review generation even if they appear on a marketplace. Those can conflict with the target platform's rules and create terrible long-term agent reputation.

---

## 2. Algora may actually be the best route to sizeable money

This is less futuristic but arguably **more economically real**.

Algora puts cash bounties directly on GitHub issues.

The process is essentially:

```text
crawler sees GitHub bounty
        ↓
understands repository
        ↓
estimates:
  difficulty
  tests
  likely competition
  token cost
  expected payout
        ↓
attempts issue
        ↓
runs tests
        ↓
opens PR
        ↓
maintainer merges
        ↓
payment
```

Visible 2026 bounties have commonly been around **$50–$2,500**, and one company testimonial says it distributed $143k through Algora. ([gigs.sh][2])

That is a *far* better economic shape than fighting 100 agents over $3 lead-generation tasks.

The problem?

Algora isn't explicitly an autonomous-agent marketplace. You're ultimately participating in normal open-source projects, so the PR needs to genuinely satisfy maintainers and you must comply with project and platform rules.

Payout is through Stripe Connect and requires the appropriate human/entity payout setup. ([gigs.sh][2])

[Algora bounties](https://algora.io/bounties?utm_source=chatgpt.com)

---

## 3. Opire is essentially another input into the same money crawler

Opire's model is similarly attractive.

As of the May verification used by gigs.sh it had:

**210 open bounties worth ~$54,959.**

Typical rewards were reportedly around **$50–$500**, with occasional much larger ones. ([gigs.sh][3])

So your agent shouldn't think:

```text
I use Algora
```

It should think:

```text
SOURCE ADAPTERS

Algora ──┐
Opire ───┤
Bounty ──┤
Clustly ─┤
...      │
         ↓
NORMALIZED OPPORTUNITY GRAPH
```

Now you've created something interesting.

---

## 4. Clustly is surprisingly serious

This one moved upward significantly after checking it.

Their new Terms are extremely explicit about how the system actually works—including things that make them look bad, which is a credibility positive.

They disclose:

**4% seller fee.**

They disclose that their escrow contract **has not yet had an independent audit**.

They disclose known issues with the live contract.

They disclose centralization of administrative keys.

They disclose exactly how seller payouts move.

That's considerably better transparency than "our AI marketplace has processed $50M!!!" with nothing underneath it. ([Clustly][5])

Their task model is almost exactly what you want:

```text
GET open tasks
→ claim
→ execute
→ submit
→ verification
→ payment
```

gigs.sh observed public jobs around **$40–$240** when it evaluated Clustly. ([gigs.sh][17])

Important eligibility detail: Clustly currently requires users to be **at least 16 and old enough locally to enter the applicable contract**. ([Clustly][5])

[Clustly](https://www.clustly.ai/?utm_source=chatgpt.com)

This is one I would monitor closely.

---

## 5. Superteam is where one good hit can matter

Superteam Earn has introduced an explicit agent API.

Agent-eligible opportunities can be discovered programmatically and submissions made through the API; then there is a human claim/payout step. ([gigs.sh][4])

gigs.sh observed agent-oriented opportunities around:

**$500–$5,000.**

That's substantially more exciting economically.

But there is a catch:

A lot of ordinary Superteam opportunities do **not** allow AI entries. The crawler therefore must read the eligibility metadata rather than blindly submit. ([gigs.sh][4])

This starts looking less like freelancing and more like your hackathon model:

```text
$2 Bounty job:
high P(win)
low payout

$2,000 Superteam bounty:
lower P(win)
huge payout

$1,000 GitHub bounty:
medium P(win)
medium execution cost
```

Now your agent allocates compute based on EV.

That is exactly the experiment I'd want.

---

## 6. Olas is real — but it proves something slightly different

Olas reports:

**10,081,700 deliveries
$108,998 total task payments
$101,509 realised Mech earnings.** ([Olas][6])

So machines really are calling machine services and paying for them.

A Mech can provide:

```text
information lookup
data transformation
LLM inference
specialized reasoning
API aggregation
image generation
analysis
```

The requester pays; the Mech performs off-chain work; the result goes back; the provider accumulates fees. ([Olas][18])

That's **service income**, not gig income.

And this is where I think the bigger opportunity sits.

Instead of:

> find 10 research gigs today

eventually your agent learns:

> I keep being paid for the same research transformation. I should sell that transformation as an endpoint.

That transition is critical.

---

## 7. Virtuals ACP proves people will hire agents, but revenue is insanely skewed

Virtuals now describes ACP as:

> agents discovering services, negotiating jobs, coordinating execution and settling payment autonomously. ([Virtuals Protocol][7])

But browsing actual agents shows the problem.

One information/data agent has roughly:

**1,980 jobs → only $19.49 total revenue.** ([Virtuals][19])

Another service has enormous job/revenue numbers. ([Virtuals][20])

So you've already got a power-law economy:

```text
thousands of dead agents
hundreds making cents
dozens making dollars
few services getting meaningful volume
```

That's precisely why **economic learning** is more interesting than merely launching an agent.

Your system should ruthlessly kill services nobody buys.

---

## 8. x402 does NOT magically make money

This deserves emphasis.

x402 is absolutely real.

The official dashboard currently says, over 30 days:

**75.41m transactions
$24.24m volume
94.06k buyers
22k sellers.** ([x402][9])

And technically monetizing an API is extremely easy. The protocol is explicitly designed for sellers charging agents or developers per HTTP request. ([x402][21])

But:

```text
x402 ≠ demand
```

Putting:

```text
/foo
price: $0.02
```

on the internet doesn't create buyers.

**Discovery and product-market fit remain the hard parts.**

That's where your station gets interesting.

---

## 9. Nevermined solves monetization—not customer acquisition

Nevermined is genuinely polished.

You can monetize:

```text
HTTP APIs
MCP servers
agents
datasets/assets
```

with:

```text
per-call
credits
subscriptions
pay-as-you-go
dynamic pricing
```

and usage/revenue observability. ([Nevermined][22])

Pricing starts at $0, with Nevermined taking around **1–2% of settled transaction volume**. ([Nevermined][23])

Great infrastructure.

But Nevermined won't magically send 100 customers to your tool.

It is:

```text
Stripe for agent services
```

not:

```text
Upwork for agents
```

Also important: Nevermined states that its service is **not directed at people under 18**, so it isn't an appropriate account platform until you meet its eligibility requirement. ([Nevermined][24])

---

## 10. MoltJobs: cool API, currently useless economically

Their architecture is almost exactly what you described:

```text
register agent
browse
apply
deliver
USDC payment
```

with REST APIs and webhooks. ([MoltJobs][25])

But today's actual jobs page says:

> **0 open jobs for AI agents.** ([MoltJobs][10])

So:

**integration priority: near zero.**

Keep an adapter for it.

Don't spend a week building around it.

---

## 11. SporeAgent worries me

This is why the deep dive matters.

Homepage:

**1,247 agents
$48,210 paid out.** ([SporeAgent][11])

Actual dashboard:

**22 agents
3 completed
$300 paid.** ([SporeAgent][26])

Its "open" jobs are around 5–6 months old. ([SporeAgent][27])

It does have a real MCP interface for:

```text
register
browse
bid
deliver
reputation
```

and proper terms including escrow and a 15% fee. ([SporeAgent][28])

So I wouldn't call it fake.

I would call it:

> **not demonstrated to have useful current liquidity.**

Do not waste compute polling stale marketplaces constantly.

---

## 12. three.ws is almost literally your dashboard idea

This one is fascinating as **research**.

Its documented economy includes:

```text
agent revenue
agent spending
paid skills
agent hiring
receipts
top customers
counterparties
P&L
spend ceilings
kill switch
revenue dashboard
x402 services
```

which is extremely close to what you initially described. ([GitHub][12])

But there's an important reality check.

Its public x402 endpoint-revenue view currently shows **no revenue in the displayed 24-hour window**, and another live operational page reported zero settlement traffic during its observation window. ([three.ws][29])

So:

> **Excellent architecture reference. Not proof that autonomous agents can currently earn meaningful money from it.**

This distinction should become one of the rules of your crawler.

---

## 13. `agent-economy` isn't a market. But steal its brain.

This repository is excellent.

It models:

```text
task
↓
planner
↓
workers bid

price
confidence
reputation

↓
expected-value scoring
↓
winner executes
↓
oracle
↓
PASS → payment
FAIL → loss
↓
immutable economic ledger
```

Its actual worker scoring formula includes reputation, estimated success probability, bounty, requested payment, expected execution cost and failure penalties. ([GitHub][13])

That is almost exactly the internal optimizer your system needs.

But no outside party is paying those agents.

It's a **market simulator/orchestrator**, not an earning source.

---

## What I would actually build

I wouldn't build another marketplace.

I'd build the thing you described:

## `AgentMoney` / `EarnOS` / whatever

```text
                    EARNING STATION
                         │
            ┌────────────┴─────────────┐
            │                          │
        ACTIVE WORK                PRODUCTS
            │                          │
      TryBounty                    x402
      Algora                       ACP
      Opire                        Olas
      Clustly                      paid MCP
      Superteam                    paid APIs
      etc.                         etc.
            │                          │
            └────────────┬─────────────┘
                         ↓
                 OPPORTUNITY DB
                         ↓
                     ECONOMIST
                         ↓
                  select attempt
                         ↓
                     EXECUTOR
                         ↓
                    VERIFIER
                         ↓
                       P&L
                         ↓
                      MEMORY
                         ↓
                     LEARNING
                         ↺
```

Every opportunity gets normalized to:

```text
reward
estimated_cost
estimated_hours
probability_of_success
competition
verification_strength
payment_reliability
reputation_gain
reusability
```

Then:

$$
EV =
P(success)\times reward
- inference\ cost
- API\ cost
- expected\ failure\ cost
$$

But I'd add one more variable:

$$
EV_{total} =
EV_{cash}
+
EV_{learning}
+
EV_{reusable\_asset}
$$

Because a $20 task that teaches the agent how to create a reusable $0.03/call API might be worth considerably more than a one-off $40 job.

---

## The exact experiment I'd run

Give the agent a small, fixed operating budget and **do not let it freely spend beyond that cap**.

Then:

1. **Connect discovery first:** gigs.sh + Bounty + Algora + Opire + eligible agent markets. gigs.sh has 46 platforms, but its current registry snapshot was last verified May 18, so the agent must independently re-check that each opportunity is still live. ([gigs.sh][14])
2. **Only attempt easily verifiable work initially:** research datasets, code fixes, extraction, API integrations, factual reports.
3. **Record every attempt**, including ones it deliberately rejects.
4. **Measure real net profit**, not gross payouts.
5. After perhaps 30–50 attempts, identify repeated capabilities.
6. Turn the best repeated capability into a paid MCP/API.
7. Publish that capability on appropriate agent-service discovery surfaces.
8. Let the agent compare **freelancing vs product revenue** and gradually allocate more resources to whichever produces better risk-adjusted returns.

Then your dashboard's killer metric becomes:

```text
LIFETIME
────────────────────────

Opportunities seen        18,294
Opportunities attempted      117
Successful                   41

Gross earned              $284.71
Compute/API costs          $38.20
Fees                       $11.82
Net earned                $234.69

ROI                         467%

ACTIVE WORK               $163.32
SERVICE REVENUE            $71.37


LEARNED STRATEGIES

Research jobs
EV / attempt                +$3.12

GitHub fixes
EV / attempt                +$8.72

Generic content
EV / attempt                -$0.41

API service
EV / day                    +$4.81
```

**That is the frontier.**

And the important conclusion from this search is that you do **not** need to wait for the ecosystem to exist. Enough primitive earning surfaces exist now to run the experiment. The serious question is whether an agent can autonomously turn a finite compute budget into **positive, repeatable, independently verified net revenue**.

I would start with **Bounty + Algora/Opire + Clustly where eligible**, use **gigs.sh only as discovery**, and treat **x402/Olas/ACP as the eventual productization layer**. MoltJobs and SporeAgent aren't worth significant attention right now. ([Bounty][1])

This market is changing fast enough that monitoring it automatically makes sense.

[1]: https://trybounty.ai/ "Bounty | Get Work Done by AI Agents"
[2]: https://www.gigs.sh/p/algora?utm_source=chatgpt.com "Algora — agent earning guide | gigs.sh"
[3]: https://www.gigs.sh/p/opire?utm_source=chatgpt.com "Opire — agent earning guide | gigs.sh"
[4]: https://gigs.sh/p/superteam-earn?utm_source=chatgpt.com "Superteam Earn — agent earning guide | gigs.sh"
[5]: https://www.clustly.ai/terms?utm_source=chatgpt.com "Clustly · terms of service"
[6]: https://olas.network/agent-economies/mech "Mech | Olas | Co-own AI"
[7]: https://www.virtuals.io/?utm_source=chatgpt.com "Virtuals Protocol | Society of AI Agents"
[8]: https://nevermined.ai/docs/solutions/agent-to-agent-monetization?utm_source=chatgpt.com "Monetize Your AI - Nevermined Documentation"
[9]: https://www.x402.org/?utm_source=chatgpt.com "x402 - Payment Required | Internet-Native Payments Standard"
[10]: https://www.molt-jobs.com/jobs "MoltJobs - Work for yourself. Get paid."
[11]: https://www.sporeagent.com/?utm_source=chatgpt.com "SporeAgent — MCP-Native Agent Task Marketplace"
[12]: https://github.com/nirholas/three.ws/blob/main/docs/agent-abilities/chapters/09-the-agent-economy.md?utm_source=chatgpt.com "three.ws/docs/agent-abilities/chapters/09-the-agent-economy.md at main · nirholas/three.ws · GitHub"
[13]: https://github.com/strangeloopcanon/agent-economy?utm_source=chatgpt.com "GitHub - strangeloopcanon/agent-economy"
[14]: https://www.gigs.sh/?utm_source=chatgpt.com "gigs.sh — The agent-native internet"
[15]: https://www.lorientlejour.com/article/1540617/sur-bounty-des-agents-dia-rivalisent-pour-decrocher-des-contrats.html?utm_source=chatgpt.com "Sur Bounty, des agents d'IA rivalisent pour décrocher des contrats - L'Orient-Le Jour"
[16]: https://trybounty.ai/terms-and-conditions "Terms and Conditions | Bounty"
[17]: https://www.gigs.sh/p/clustly?utm_source=chatgpt.com "Clustly — agent earning guide | gigs.sh"
[18]: https://olas.network/mech-marketplace "Mech Marketplace | Olas | Co-own AI"
[19]: https://app.virtuals.io/acp/agent/019dcc66-4241-7ac4-b21e-8dd159898576?utm_source=chatgpt.com "Virtuals Protocol | Society of AI Agents"
[20]: https://app.virtuals.io/acp/agent/019e4f32-23d3-78eb-80bc-9545cdc49328?utm_source=chatgpt.com "Virtuals Protocol | Society of AI Agents"
[21]: https://docs.x402.org/introduction?utm_source=chatgpt.com "Welcome to x402 - x402"
[22]: https://nevermined.ai/docs/api-reference/typescript/payment-plans?utm_source=chatgpt.com "Payment Plans - Nevermined Documentation"
[23]: https://nevermined.ai/pricing/?utm_source=chatgpt.com "Pricing - Start Free, Pay When Money Moves | Nevermined"
[24]: https://nevermined.app/legal/data-privacy?utm_source=chatgpt.com "Privacy Policy — Nevermined"
[25]: https://www.molt-jobs.com/ "MoltJobs - Work for yourself. Get paid."
[26]: https://www.sporeagent.com/dashboard?utm_source=chatgpt.com "SporeAgent — MCP-Native Agent Task Marketplace"
[27]: https://sporeagent.com/tasks?utm_source=chatgpt.com "SporeAgent — MCP-Native Agent Task Marketplace"
[28]: https://sporeagent.com/docs?utm_source=chatgpt.com "Documentation — SporeAgent"
[29]: https://three.ws/x402-revenue?lang=kn&utm_source=chatgpt.com "Endpoint Revenue · three.ws"
