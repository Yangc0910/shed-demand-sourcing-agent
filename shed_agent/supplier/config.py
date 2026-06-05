from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_SUPPLIER_CONFIG_PATH = Path("config/supplier_config.json")


@dataclass
class SupplierConfig:
    target_product_types: list[str] = field(default_factory=lambda: ["4x6_horizontal", "6x5_vertical"])
    preferred_batch_min: int = 6
    preferred_batch_max: int = 8
    maximum_initial_batch: int = 10
    destination: str = "Boston / East Coast US"
    rfq_price_tiers: list[int] = field(default_factory=lambda: [5, 10, 20, 50])
    enable_llm_extraction: bool = True
    enable_llm_drafting: bool = True
    llm_model: str = "gpt-4.1-mini"
    cache_llm_results: bool = True
    llm_cache_dir: str = "data/supplier_llm_cache"
    report_output_directory: str = "reports"
    outbound_mode: str = "human_approved"
    score_thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "strongCandidate": 8.0,
            "watch": 6.0,
            "needsMoreInfo": 4.0,
        }
    )
    target_unit_costs: dict[str, float] = field(
        default_factory=lambda: {
            "4x6_horizontal": 260,
            "6x5_vertical": 360,
        }
    )
    manageable_gross_weight_kg: float = 120
    manageable_cartons_per_unit: int = 3


def load_supplier_config(path: Path = DEFAULT_SUPPLIER_CONFIG_PATH) -> SupplierConfig:
    if not path.exists():
        return SupplierConfig()
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return SupplierConfig(
        target_product_types=data.get("targetProductTypes", ["4x6_horizontal", "6x5_vertical"]),
        preferred_batch_min=data.get("preferredBatchMin", 6),
        preferred_batch_max=data.get("preferredBatchMax", 8),
        maximum_initial_batch=data.get("maximumInitialBatch", 10),
        destination=data.get("destination", "Boston / East Coast US"),
        rfq_price_tiers=data.get("rfqPriceTiers", [5, 10, 20, 50]),
        enable_llm_extraction=data.get("enableLLMExtraction", True),
        enable_llm_drafting=data.get("enableLLMDrafting", True),
        llm_model=data.get("llmModel", "gpt-4.1-mini"),
        cache_llm_results=data.get("cacheLLMResults", True),
        llm_cache_dir=data.get("llmCacheDir", "data/supplier_llm_cache"),
        report_output_directory=data.get("reportOutputDirectory", "reports"),
        outbound_mode=data.get("outboundMode", "human_approved"),
        score_thresholds=data.get(
            "scoreThresholds",
            {"strongCandidate": 8.0, "watch": 6.0, "needsMoreInfo": 4.0},
        ),
        target_unit_costs=data.get("targetUnitCosts", {"4x6_horizontal": 260, "6x5_vertical": 360}),
        manageable_gross_weight_kg=data.get("manageableGrossWeightKg", 120),
        manageable_cartons_per_unit=data.get("manageableCartonsPerUnit", 3),
    )
