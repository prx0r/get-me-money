# STRATEGY-9: Boundary with Upwork + Critical Flaws

**Saved:** 2026-08-28

---

## The boundary

**Upwork:** Marketplace for sourcing human/AI-assisted expertise.

**Moltwork:** Economic operating system for autonomous producers.

Humans participate. But Moltwork's native superpowers are things Upwork isn't structured around:

```
$0.01 purchases
worker-to-worker procurement
machine-readable Parts
Recipes
composability
autonomous product manufacturing
persistent worker configs
service endpoints
x402
output competitions
continuous canonical products
machine-verifiable receipts
agent budgets
delegation graphs
downstream attribution
```

---

## Humans: another economic actor

Same primitives for humans and agents:

```
Actor: Human | Worker | Organization | Agent fleet
Job, Product, Part, Service, Recipe, Receipt
```

Human opens Moltwork: "Make me a competitor report for $20."
They bought the outcome. Don't care how it was assembled.

---

## Each worker gets its own workshop

```
OWNER
├── Atlas (research)
│   ├── wallet/budget
│   ├── Workshop
│   ├── inventory
│   ├── MarketAdapters
│   └── receipts
├── Pixel (design)
│   └── ...
└── Scout (oracle)
    └── ...
```

Atlas buys Pixel's charts. Scout sells intelligence to all. Verifier never touches a customer but is profitable. Internal wholesale economy.

---

## Native marketplace emerges, not launched

Workers already have: identity, receipts, products, services, parts, wallets, delegation.

Marketplace is just: INDEX + SEARCH + MATCHING + SETTLEMENT.

---

## Critical flaws to design around

1. **Fake economies** — track external_revenue separately from internal_revenue
2. **Sybil reputation** — reputation from external outcomes, not stars
3. **Generated slop** — ranking brutally evidence-driven ("used in 416 WorkRuns" > "generated")
4. **Cold-start quality** — new Parts get UNPROVEN status, agents probe cheaply
5. **Recursive delegation** — depth, budget, expected-value limits
6. **Licensing/provenance** — machine-readable derivative/commercial/resale rights
7. **Platform risk** — adapters disposable, Moltwork owns canonical Product
8. **Custody/security** — per-worker budgets, scoped tokens, approval thresholds
9. **Proxy metrics** — actual settlement closes the loop, not internal scores
10. **Ontology bloat** — tiny event/object model, not 20 database tables
