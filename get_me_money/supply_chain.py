"""Supply Chain — Parts, Builds, Products, Provenance.

The three levels of the Moltwork wholesale economy:

  Part      — composable input (dataset, skill, template, service)
  Build     — known composition of Parts (recipe for producing something)
  Product   — finished useful thing (report, code, dataset, service)

Plus provenance: which Parts produced which Products, with economic evidence.

Every completed SubmissionRun can generate:
  - a new Part (if the output is reusable)
  - a new Build (if the process is reusable)
  - a Product (the finished artifact)
  - provenance links connecting them
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Part:
    """A composable input — something used to make other things."""
    id: str = ""
    name: str = ""
    version: str = "1.0.0"
    type: str = ""  # "dataset", "skill", "template", "service", "evidence", "config"

    # What it needs and produces
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)

    # Compatibility
    compatibility: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    # Source
    creator_worker: str = ""
    source_run: str = ""  # SubmissionRun ID that created this
    created_at: float = field(default_factory=time.time)

    # Quality
    validations: list[str] = field(default_factory=list)
    benchmarks: dict[str, float] = field(default_factory=dict)

    # Economics
    price: float = 0.0
    purchases: int = 0
    downstream_uses: int = 0
    downstream_revenue: float = 0.0

    # Provenance
    derived_from: list[str] = field(default_factory=list)  # Part IDs

    def to_dict(self) -> dict:
        return asdict(self)

    def content_hash(self) -> str:
        raw = f"{self.name}:{self.version}:{self.type}:{json.dumps(self.inputs)}:{json.dumps(self.outputs)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class Build:
    """A known composition of Parts — a recipe for producing something."""
    id: str = ""
    name: str = ""
    description: str = ""

    # What it uses
    parts: list[str] = field(default_factory=list)  # Part IDs

    # How it works
    steps: list[str] = field(default_factory=list)

    # What it produces
    output_type: str = ""

    # Economics
    estimated_cost: float = 0.0
    historical_acceptance: float = 0.0
    uses: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Product:
    """A finished useful thing — the output of a Build or direct creation."""
    id: str = ""
    name: str = ""
    type: str = ""  # "report", "dataset", "code", "service", "artifact"

    # Source
    build_id: str = ""  # which Build produced this
    run_id: str = ""  # which SubmissionRun produced this
    worker_id: str = ""
    created_at: float = field(default_factory=time.time)

    # Quality
    judge_score: float = 0.0
    verified: bool = False

    # Economics
    price: float = 0.0
    purchases: int = 0
    revenue: float = 0.0

    # Provenance
    parts_used: list[str] = field(default_factory=list)  # Part IDs
    derived_from: list[str] = field(default_factory=list)  # Product IDs

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Provenance:
    """Links between Parts, Builds, and Products with economic evidence."""
    product_id: str = ""
    build_id: str = ""
    parts_used: list[str] = field(default_factory=list)
    run_id: str = ""

    # Economic evidence
    total_cost: float = 0.0
    judge_score: float = 0.0
    accepted: bool = False
    revenue: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class SupplyChain:
    """Manages Parts, Builds, Products, and Provenance.

    The supply chain is the bridge between "doing work" and "market intelligence."
    Every completed job can produce reusable Parts and Products.
    Every Part's downstream usage is tracked for economic attribution.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.parts_dir = data_dir / "parts"
        self.builds_dir = data_dir / "builds"
        self.products_dir = data_dir / "products"
        self.provenance_dir = data_dir / "provenance"
        for d in [self.parts_dir, self.builds_dir, self.products_dir, self.provenance_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def add_part(self, part: Part) -> str:
        """Add a Part to the supply chain."""
        if not part.id:
            part.id = f"part-{part.content_hash()}"
        part.save(self.parts_dir / part.id)
        return part.id

    def add_build(self, build: Build) -> str:
        """Add a Build to the supply chain."""
        if not build.id:
            build.id = f"build-{hashlib.sha256(build.name.encode()).hexdigest()[:12]}"
        build.save(self.builds_dir / build.id)
        return build.id

    def add_product(self, product: Product) -> str:
        """Add a Product to the supply chain."""
        if not product.id:
            product.id = f"product-{hashlib.sha256(product.name.encode()).hexdigest()[:12]}"
        product.save(self.products_dir / product.id)
        return product.id

    def record_provenance(self, prov: Provenance) -> None:
        """Record provenance — which Parts produced which Product."""
        prov_file = self.provenance_dir / f"{prov.product_id}.json"
        prov_file.write_text(json.dumps(prov.to_dict(), indent=2))

        # Update downstream usage for each Part used
        for part_id in prov.parts_used:
            part = self.load_part(part_id)
            if part:
                part.downstream_uses += 1
                if prov.revenue > 0:
                    part.downstream_revenue += prov.revenue
                part.save(self.parts_dir / part.id)

    def load_part(self, part_id: str) -> Part | None:
        path = self.parts_dir / part_id / "part.json"
        if not path.exists():
            path = self.parts_dir / f"{part_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        part = Part()
        for k, v in data.items():
            if hasattr(part, k):
                setattr(part, k, v)
        return part

    def list_parts(self, type_filter: str = "") -> list[Part]:
        parts = []
        for f in self.parts_dir.glob("*.json"):
            data = json.loads(f.read_text())
            part = Part()
            for k, v in data.items():
                if hasattr(part, k):
                    setattr(part, k, v)
            if not type_filter or part.type == type_filter:
                parts.append(part)
        return sorted(parts, key=lambda p: p.downstream_revenue, reverse=True)

    def from_submission_run(self, run_data: dict) -> dict:
        """Extract Parts, Products, and Provenance from a SubmissionRun.

        This is the bridge: completed work → reusable economic assets.
        """
        result = {"parts": [], "products": [], "provenance": None}

        # The artifact becomes a Product
        if run_data.get("content"):
            product = Product(
                name=run_data.get("task_title", "untitled"),
                type=run_data.get("category", "artifact"),
                run_id=run_data.get("id", ""),
                worker_id=run_data.get("worker_id", ""),
                judge_score=run_data.get("judge_score", 0),
                verified=run_data.get("accepted", False),
                parts_used=run_data.get("skills_used", []),
            )
            product_id = self.add_product(product)
            result["products"].append(product_id)

            # Record provenance
            prov = Provenance(
                product_id=product_id,
                run_id=run_data.get("id", ""),
                parts_used=run_data.get("skills_used", []),
                total_cost=run_data.get("total_cost", 0),
                judge_score=run_data.get("judge_score", 0),
                accepted=run_data.get("accepted", False),
                revenue=run_data.get("reward", 0),
            )
            self.record_provenance(prov)
            result["provenance"] = prov.to_dict()

        return result


# Patch save/load onto dataclasses
def _part_save(self, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path if path.suffix == ".json" else path.with_suffix(".json")
    target.write_text(json.dumps(self.to_dict(), indent=2))

def _build_save(self, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path if path.suffix == ".json" else path.with_suffix(".json")
    target.write_text(json.dumps(self.to_dict(), indent=2))

def _product_save(self, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path if path.suffix == ".json" else path.with_suffix(".json")
    target.write_text(json.dumps(self.to_dict(), indent=2))

Part.save = _part_save
Build.save = _build_save
Product.save = _product_save
