# NORTHSTAR 8 — Human Queue as First-Class Subsystem
**Date:** 2026-08-28 (eighth pass)

---

## Core principle

Agent autonomous by default; human only handles irreversible, identity-bound, legal, high-risk, or ambiguous actions.

## Human task types

```
AUTH        OAuth / API key / account connection
IDENTITY    KYC / age / identity verification
LEGAL       Terms acceptance / contract / policy change
APPROVAL    Agent wants permission for significant action
PAYMENT     Funding / payout / withdrawal
SECRET      API credential required
AMBIGUITY   Agent genuinely cannot infer user intent
SECURITY    Suspicious skill/tool/site needs review
EXCEPTION   Agent got stuck after automated recovery
```

## Task structure

```json
{
  "id": "human_2938",
  "type": "AUTH",
  "priority": "high",
  "title": "Connect GitHub",
  "reason": "Required to submit Algora PR",
  "job_id": "algora_819",
  "estimated_value": 102.40,
  "deadline": "2026-08-29T18:00:00Z",
  "agent_progress": ["inspected issue", "estimated EV", "prepared plan"],
  "requested_action": "oauth_github",
  "resume_event": "github_connected"
}
```

## EV priority sorting

```
HumanPriority = (ExpectedValue × Urgency) / EstimatedHumanEffort
```

"Connect GitHub: 30 seconds, unlocks $177 EV" → TOP
"Sign into obscure marketplace: 5 minutes, one $2 opportunity" → LOW

## Dashboard homepage

```
EARNBOX                          ● LIVE

Agent balance                  $14.82
Today's net                     +$3.91
Daily target                    $5.00
████████████████░░░░ 78%

NEEDS YOU                        3

[!] Connect GitHub             HIGH
    Unlocks 4 opportunities / ~$177 EV
    [CONNECT]

[$] Claim Superteam prize      $50
    Submission accepted
    [CLAIM]

[?] Approve $0.42 tool purchase
    Expected job value: $18
    [APPROVE] [DENY]
```

## Credential vault

```
Human → Credential Vault → scoped capability token → job runtime
```

Hermes gets minimum capability, not entire .env.

## Policy-based autonomy

```
Research API purchases < $0.50        AUTO
Deployment < $1/day                   AUTO
New marketplace account               ASK
OAuth connection                      ASK
GitHub PR submission                  AUTO
Financial withdrawal                  ASK
Legal terms                           ALWAYS ASK
KYC                                   ALWAYS HUMAN
```

## Attention budget metrics

```
AUTONOMY SCORE             94%
Agent operations           418
Human interventions          3
Human time                 2m 14s
Net revenue / human hour = $164
```

## Batch requests

Bad: 4 separate prompts at 08:10, 08:12, 08:15, 08:22
Good: "YOUR AGENT NEEDS 3 THINGS — Completing these unlocks 17 opportunities worth ~$241 EV"

## Event stream

```
HumanTaskCreated → HumanTaskNotified → HumanTaskViewed
→ HumanTaskApproved/Denied → HumanTaskResolved → JobResumed
```

## Three surfaces

1. **Money**: earnings, cost, wallet, P&L, targets
2. **Agent**: what it's doing, why, skills, jobs, learning
3. **Needs You**: connections, approvals, KYC/legal, payout claims, exceptions

## Product promise

> Launch an autonomous earning agent. It handles the technical work and only contacts you when it genuinely needs a human.
