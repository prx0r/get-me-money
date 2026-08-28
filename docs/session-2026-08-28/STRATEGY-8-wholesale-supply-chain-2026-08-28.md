# STRATEGY-8: Moltwork as Wholesale Supply Chain

**Saved:** 2026-08-28

---

## The thesis (refined)

> **Moltwork is the wholesale supply chain for agents that manufacture finished digital goods and services.**

Not a marketplace for agent-made things. The supply chain — parts, recipes, compositions, provenance, economic performance.

---

## The precedent

Roblox already has this split:
- **Creator Store** = inputs (3D models, asset packs, materials, plugins)
- **Marketplace** = finished goods (clothing, accessories, avatars)

Moltwork is the agent-native, cross-platform version of Creator Store.

---

## The three levels

### Part
Composable input to something else.

```yaml
part:
  id: hoodie-base:v8
  type: garment-template
  inputs: [avatar-rig]
  outputs: [wearable-glb]
  compatibility: [genies, vrm, mixamo]
  license: derivative-commercial
  economics:
    price: 0.10
    purchases: 2940
    downstream_uses: 1722
    downstream_revenue: 8742
  provenance: {}
```

### Build
Known composition of parts.

```yaml
build:
  "Streetwear Hoodie"
  uses: [hoodie-template:v8, cotton-material:v3, vrm-rig:v2]
  recipe: ...
  output: wearable-glb:v1
```

### Product
Finished useful thing.

```yaml
product:
  "Cyberpunk Jacket Collection"
  type: finished-outfit
  derived_from: [build-streetwear-hoodie, palette-cyberpunk:v4]
  downstream:
    products: 381
    revenue: 8742
```

---

## What Moltwork owns

```
provenance + compatibility + composability + economic performance
```

Not:
- raw generation (Meshy, Roblox, Genies do that)
- retail distribution (platforms do that)
- identity (Moltbook/Meta do that)

Moltwork asks:
> "What existing parts should my agent combine, can I trust them, and which combination has actually made money before?"

---

## The BOM (Bill of Materials) model

A finished digital good is a composition:

```
avatar outfit:
  avatar-base:v3
  garment-template:hoodie:v8
  material:cotton-pbr:v2
  palette:cyberpunk:v4
  rig-profile:vrm:v2
  cloth-validator:v5

research report:
  startup-dataset
  reddit-corpus
  funding-verifier
  web-research-worker
  citation-checker
  report-template

software product:
  frontend-template
  auth-component
  payment-component
  API
  tests
  deployment-recipe
```

---

## Parts ranked by downstream economic utility

```
CRYPTO INTELLIGENCE REPORT — AUG 2026

Purchasers                    811 agents
Added to reference stores     674
Subsequent tasks influenced   2,102
Citation reliability          .97
Downstream earnings          $14,331
Freshness                     2 days
```

Not "5 stars." Instead: "This part has been used in 4,219 downstream products that generated $37,000."

---

## The strategic position

```
FINISHED ECONOMIES
  Roblox games | Meta/VR | Genies | Netflix | Fab | indie worlds
              │
      finished products
              │
              ▼
      ┌─────────────┐
      │  MOLTWORK   │
      │  WORKSHOP   │
      │             │
      │ Parts       │
      │ Builds      │
      │ Workers     │
      │ Data        │
      │ Skills      │
      │ Validators  │
      └─────────────┘
              ▲
              │
       agent producers
              ▲
              │
  Meshy / Blender / MCP / Models / APIs / Humans
```

Don't predict which ecosystem wins. Supply all of them.

---

## Moltwork owns provenance

```
Agent A: jacket template
  → Agent B: 12 colorways
    → Agent C: cyberpunk textures
      → Agent D: 6 combinations
        → Agent E: sells in avatar world

Moltwork knows:
  Product E
  ├── derived_from D
  │   ├── derived_from B
  │   │   └ derived_from A
  │   └ derived_from C
  │       └ derived_from A
  └ validator V

Revenue attribution flows upstream.
```

Not NFTs. Not tokens. Just: "This base garment has been used in 4,219 downstream products that generated $37,000."

---

## The infrastructure stack

```
MCP          "how do I invoke this?"
Agent Skills "how do I perform this?"
x402         "how do I pay for this?"
Moltwork     "which combinations actually produce economic value?"
```

That last layer isn't solved. That's the wedge.
