"""Factories — canonical production pipelines for different product types.

A Factory defines:
  - the production steps
  - the Parts needed
  - the output format
  - which MarketAdapters can distribute it

A Factory is NOT a marketplace. It's a manufacturing system.
The same Factory output can go to many markets via adapters.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FactoryStep:
    name: str = ""
    worker: str = ""  # which workshop worker
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0


@dataclass
class Factory:
    name: str = ""
    description: str = ""
    category: str = ""  # "knowledge", "media", "software", "virtual_goods", "experiences", "work"

    steps: list[FactoryStep] = field(default_factory=list)
    required_parts: list[str] = field(default_factory=list)
    output_type: str = ""

    # Which markets can distribute this
    distribution: list[str] = field(default_factory=list)

    estimated_cost: float = 0.0
    historical_acceptance: float = 0.0


# ─── Knowledge Factories ─────────────────────────────────────────────

REPORT_FACTORY = Factory(
    name="Report Factory",
    description="Produce research reports, market analysis, competitive intelligence",
    category="knowledge",
    steps=[
        FactoryStep("research", "scout", ["topic"], ["findings"], 0.08),
        FactoryStep("verify", "scout", ["findings"], ["verified_facts"], 0.03),
        FactoryStep("analyze", "oracle", ["verified_facts"], ["analysis"], 0.05),
        FactoryStep("write", "scout", ["analysis"], ["draft"], 0.10),
        FactoryStep("critique", "oracle", ["draft"], ["critique"], 0.03),
        FactoryStep("revise", "scout", ["draft", "critique"], ["final"], 0.08),
    ],
    output_type="report",
    distribution=["moltwork", "gumroad", "aws_market"],
    estimated_cost=0.37,
)

DATASET_FACTORY = Factory(
    name="Dataset Factory",
    description="Produce structured datasets, research corpora, evidence packs",
    category="knowledge",
    steps=[
        FactoryStep("collect", "scout", ["source"], ["raw_data"], 0.05),
        FactoryStep("clean", "oracle", ["raw_data"], ["clean_data"], 0.03),
        FactoryStep("structure", "oracle", ["clean_data"], ["structured"], 0.04),
        FactoryStep("validate", "oracle", ["structured"], ["validated"], 0.02),
    ],
    output_type="dataset",
    distribution=["moltwork", "aws_market", "databricks"],
    estimated_cost=0.14,
)

# ─── Software Factories ──────────────────────────────────────────────

APP_FACTORY = Factory(
    name="App Factory",
    description="Produce mobile apps, web apps, browser extensions",
    category="software",
    steps=[
        FactoryStep("spec", "oracle", ["pain_point"], ["spec"], 0.05),
        FactoryStep("code", "forge", ["spec"], ["codebase"], 0.15),
        FactoryStep("test", "forge", ["codebase"], ["tested_code"], 0.05),
        FactoryStep("review", "forge", ["tested_code"], ["reviewed"], 0.03),
        FactoryStep("package", "relay", ["reviewed"], ["package"], 0.04),
    ],
    output_type="app",
    distribution=["apple", "google_play", "github_market", "itchio"],
    estimated_cost=0.32,
)

MCP_FACTORY = Factory(
    name="MCP Server Factory",
    description="Produce MCP servers for agent tool use",
    category="software",
    steps=[
        FactoryStep("spec", "oracle", ["capability"], ["spec"], 0.03),
        FactoryStep("code", "forge", ["spec"], ["server"], 0.10),
        FactoryStep("test", "forge", ["server"], ["tested"], 0.03),
        FactoryStep("package", "relay", ["tested"], ["package"], 0.02),
    ],
    output_type="mcp_server",
    distribution=["github_market", "aws_market", "apify"],
    estimated_cost=0.18,
)

# ─── Media Factories ─────────────────────────────────────────────────

VIDEO_FACTORY = Factory(
    name="Video Factory",
    description="Produce videos, podcasts, tutorials",
    category="media",
    steps=[
        FactoryStep("research", "scout", ["topic"], ["research"], 0.08),
        FactoryStep("script", "scout", ["research"], ["script"], 0.06),
        FactoryStep("storyboard", "scout", ["script"], ["storyboard"], 0.04),
        FactoryStep("produce", "relay", ["storyboard"], ["footage"], 0.15),
        FactoryStep("edit", "relay", ["footage"], ["edit"], 0.08),
        FactoryStep("thumbnail", "forge", ["edit"], ["thumbnail"], 0.02),
    ],
    output_type="video",
    distribution=["youtube", "itchio", "gumroad"],
    estimated_cost=0.43,
)

# ─── Asset Factories ─────────────────────────────────────────────────

ASSET_FACTORY = Factory(
    name="Asset Factory",
    description="Produce 3D models, templates, design assets",
    category="virtual_goods",
    steps=[
        FactoryStep("design", "oracle", ["brief"], ["design"], 0.05),
        FactoryStep("create", "forge", ["design"], ["asset"], 0.20),
        FactoryStep("validate", "oracle", ["asset"], ["validated"], 0.03),
        FactoryStep("package", "relay", ["validated"], ["package"], 0.02),
    ],
    output_type="asset",
    distribution=["roblox", "superhive", "itchio", "etsy"],
    estimated_cost=0.30,
)

# ─── Registry ─────────────────────────────────────────────────────────

FACTORIES = {
    "report": REPORT_FACTORY,
    "dataset": DATASET_FACTORY,
    "app": APP_FACTORY,
    "mcp": MCP_FACTORY,
    "video": VIDEO_FACTORY,
    "asset": ASSET_FACTORY,
}


def get_factory(name: str) -> Factory | None:
    return FACTORIES.get(name)


def list_factories() -> list[Factory]:
    return list(FACTORIES.values())
