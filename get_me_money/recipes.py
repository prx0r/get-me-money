"""Recipes — reusable production processes.

A recipe is: given this type of work + available tools → here's how to produce output.

Recipes are the bridge between "what exists" (oracle) and "what to do" (execution).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RecipeStep:
    """One step in a production process."""
    name: str = ""
    tool: str = ""  # which tool/service to use
    input_from: str = ""  # previous step name
    output: str = ""  # what this step produces
    estimated_cost: float = 0.0
    can_skip: bool = False


@dataclass
class Recipe:
    """A reusable production process.

    Given: work type + available tools → output
    """
    id: str = ""
    name: str = ""
    description: str = ""

    # What this recipe produces
    work_type: str = ""  # "data", "research", "code", "content", "tool"
    output_type: str = ""  # "report", "dataset", "code", "service"

    # What it needs
    required_tools: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)

    # How it works
    steps: list[RecipeStep] = field(default_factory=list)

    # Economics
    estimated_cost: float = 0.0
    estimated_time_minutes: float = 0.0
    success_rate: float = 0.0
    uses: int = 0

    def can_execute(self, available_tools: list[str]) -> bool:
        """Can this recipe run with the tools we have?"""
        available = set(t.lower() for t in available_tools)
        required = set(t.lower() for t in self.required_tools)
        return required.issubset(available)


# ─── Starter recipes ─────────────────────────────────────────────────

RECIPES = {
    "research-report": Recipe(
        id="research-report",
        name="Research Report",
        description="Research a topic and produce a structured report",
        work_type="research",
        output_type="report",
        required_tools=["web-search", "browser"],
        required_skills=["research", "analysis", "writing"],
        steps=[
            RecipeStep("research", "web-search", "", "findings"),
            RecipeStep("verify", "web-search", "findings", "verified"),
            RecipeStep("analyze", "browser", "verified", "analysis"),
            RecipeStep("write", "", "analysis", "report"),
        ],
        estimated_cost=0.30,
        estimated_time_minutes=15,
        success_rate=0.80,
    ),
    "data-extraction": Recipe(
        id="data-extraction",
        name="Data Extraction",
        description="Extract structured data from web sources",
        work_type="data",
        output_type="dataset",
        required_tools=["web-search", "browser"],
        required_skills=["parsing", "data"],
        steps=[
            RecipeStep("scrape", "browser", "", "raw_data"),
            RecipeStep("parse", "", "raw_data", "structured"),
            RecipeStep("validate", "", "structured", "validated"),
        ],
        estimated_cost=0.15,
        estimated_time_minutes=10,
        success_rate=0.85,
    ),
    "code-fix": Recipe(
        id="code-fix",
        name="Code Fix",
        description="Fix a bug or implement a feature",
        work_type="code",
        output_type="code",
        required_tools=["github", "terminal"],
        required_skills=["coding", "testing"],
        steps=[
            RecipeStep("understand", "", "", "spec"),
            RecipeStep("implement", "terminal", "spec", "code"),
            RecipeStep("test", "terminal", "code", "tested"),
            RecipeStep("review", "", "tested", "reviewed"),
        ],
        estimated_cost=0.20,
        estimated_time_minutes=20,
        success_rate=0.75,
    ),
    "tool-builder": Recipe(
        id="tool-builder",
        name="Tool Builder",
        description="Build an API, MCP server, or Actor",
        work_type="tool",
        output_type="service",
        required_tools=["terminal", "github"],
        required_skills=["coding", "api-design"],
        steps=[
            RecipeStep("spec", "", "", "spec"),
            RecipeStep("build", "terminal", "spec", "code"),
            RecipeStep("test", "terminal", "code", "tested"),
            RecipeStep("package", "", "tested", "package"),
        ],
        estimated_cost=0.25,
        estimated_time_minutes=25,
        success_rate=0.70,
    ),
    "content-generation": Recipe(
        id="content-generation",
        name="Content Generation",
        description="Generate articles, documentation, templates",
        work_type="content",
        output_type="content",
        required_tools=["web-search"],
        required_skills=["writing", "research"],
        steps=[
            RecipeStep("research", "web-search", "", "sources"),
            RecipeStep("draft", "", "sources", "draft"),
            RecipeStep("review", "", "draft", "final"),
        ],
        estimated_cost=0.10,
        estimated_time_minutes=8,
        success_rate=0.85,
    ),
}


def find_recipe(work_type: str, available_tools: list[str]) -> Recipe | None:
    """Find the best recipe for a work type given available tools."""
    for recipe in RECIPES.values():
        if recipe.work_type == work_type and recipe.can_execute(available_tools):
            return recipe
    return None


def list_recipes() -> list[Recipe]:
    return list(RECIPES.values())
