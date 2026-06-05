from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any
from uuid import uuid4


LISTING_STATUSES = {"active", "disappeared", "sold", "unknown"}
SOURCE_TYPES = {
    "manual",
    "craigslist_rss",
    "watchlist_url",
    "email_future",
    "retail_comparable",
    "amazon_retail",
    "walmart_retail",
    "homedepot_retail",
    "lowes_retail",
    "costco_retail",
    "nextdoor_snippet",
    "local_facebook_group_snippet",
    "manual_local_post",
    "alibaba_supplier",
    "made_in_china_supplier",
    "1688_supplier",
    "supplier_rfq",
    "facebook_marketplace_playwright",
    "sample",
}
LOCAL_DEMAND_SOURCE_TYPES = {
    "manual",
    "craigslist_rss",
    "watchlist_url",
    "facebook_marketplace_playwright",
    "nextdoor_snippet",
    "local_facebook_group_snippet",
    "manual_local_post",
    "sample",
}
RETAIL_BENCHMARK_SOURCE_TYPES = {
    "retail_comparable",
    "amazon_retail",
    "walmart_retail",
    "homedepot_retail",
    "lowes_retail",
    "costco_retail",
}
SUPPLIER_INVENTORY_SOURCE_TYPES = {
    "alibaba_supplier",
    "made_in_china_supplier",
    "1688_supplier",
    "supplier_rfq",
}
PRODUCT_TYPES = {
    "horizontal_shed",
    "vertical_shed",
    "deck_box",
    "large_shed",
    "garden_dome",
    "greenhouse",
    "canopy_gazebo",
    "patio_storage",
    "bike_storage",
    "backyard_structure",
    "shed_accessory",
    "other",
}
TARGET_SKU_FITS = {"4x6_horizontal", "6x5_vertical", "adjacent_expansion", "not_relevant"}


@dataclass
class PricePoint:
    price: float
    date_seen: str


@dataclass
class RetailComparable:
    retailer: str
    product_title: str
    url: str = ""
    brand: str = ""
    size: str = ""
    product_type: str = "other"
    price: float | None = None
    rating: float | None = None
    review_count: int | None = None
    delivery_available: bool = False
    delivery_cost_if_known: str = ""
    assembly_service_available: bool = False
    return_policy_notes: str = ""
    warranty_notes: str = ""
    raw_text: str = ""
    date_seen: str = field(default_factory=lambda: date.today().isoformat())
    notes: str = ""

    def to_observation(self, source_type: str = "retail_comparable") -> "MarketObservation":
        return MarketObservation(
            source=self.retailer,
            source_type=source_type,
            title=self.product_title,
            url=self.url,
            price=self.price,
            size_raw=self.size,
            brand_raw=self.brand,
            inferred_brand=self.brand or "unknown",
            description_raw=self.raw_text,
            product_type=self.product_type,
            delivery_mentioned=self.delivery_available,
            assembly_mentioned=self.assembly_service_available,
            date_seen=self.date_seen,
            last_seen=self.date_seen,
            listing_status="active",
            notes=self.notes,
            retailer=self.retailer,
            product_title=self.product_title,
            rating=self.rating,
            review_count=self.review_count,
            delivery_available=self.delivery_available,
            delivery_cost_if_known=self.delivery_cost_if_known,
            assembly_service_available=self.assembly_service_available,
            return_policy_notes=self.return_policy_notes,
            warranty_notes=self.warranty_notes,
        )


@dataclass
class MarketObservation:
    source: str
    description_raw: str
    source_type: str = "manual"
    title: str = ""
    url: str = ""
    price: float | None = None
    location: str = ""
    distance: str = ""
    size_raw: str = ""
    inferred_size_category: str = "unknown"
    brand_raw: str = ""
    inferred_brand: str = "unknown"
    condition: str = "unknown"
    product_type: str = "other"
    target_sku_fit: str = "not_relevant"
    delivery_mentioned: bool = False
    assembly_mentioned: bool = False
    pickup_required: bool = False
    permit_or_placement_mentions: bool = False
    date_seen: str = field(default_factory=lambda: date.today().isoformat())
    last_seen: str = field(default_factory=lambda: date.today().isoformat())
    listing_status: str = "unknown"
    price_history: list[PricePoint] = field(default_factory=list)
    notes: str = ""
    search_keyword: str = ""
    thumbnail_url: str = ""
    image_urls: list[str] = field(default_factory=list)
    posted_time: str = ""
    source_metadata: dict[str, Any] = field(default_factory=dict)
    llm_analysis: dict[str, Any] = field(default_factory=dict)
    llm_content_hash: str = ""
    analysis_quality: str = "fallback_only"
    extraction_notes: list[str] = field(default_factory=list)
    demand_relevance_score: int = 1
    price_attractiveness_score: int = 1
    local_competitive_signal_score: int = 1
    delivery_assembly_gap_score: int = 1
    overall_signal_score: float = 1.0
    score_notes: list[str] = field(default_factory=list)
    change_notes: list[str] = field(default_factory=list)
    retailer: str = ""
    product_title: str = ""
    rating: float | None = None
    review_count: int | None = None
    delivery_available: bool = False
    delivery_cost_if_known: str = ""
    assembly_service_available: bool = False
    return_policy_notes: str = ""
    warranty_notes: str = ""
    fetch_status: str = ""
    verification_status: str = "unverified"
    demand_match: str = "unknown"
    false_positive_risk: str = "unknown"
    evidence_quality: str = "unknown"
    learning_notes: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def raw_text(self) -> str:
        return self.description_raw

    @property
    def size(self) -> str:
        return self.size_raw

    @property
    def brand(self) -> str:
        return self.brand_raw or self.inferred_brand

    @property
    def is_useful_comparable(self) -> bool:
        return (
            not self.is_retail_comparable
            and self.target_sku_fit in {"4x6_horizontal", "6x5_vertical"}
            and self.price is not None
        )

    @property
    def is_adjacent_expansion(self) -> bool:
        return self.target_sku_fit == "adjacent_expansion"

    @property
    def is_retail_comparable(self) -> bool:
        return self.source_type in RETAIL_BENCHMARK_SOURCE_TYPES

    @property
    def is_supplier_inventory_source(self) -> bool:
        return self.source_type in SUPPLIER_INVENTORY_SOURCE_TYPES

    @property
    def is_local_demand_source(self) -> bool:
        return self.source_type in LOCAL_DEMAND_SOURCE_TYPES and not self.is_retail_comparable and not self.is_supplier_inventory_source

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["price_history"] = [asdict(point) for point in self.price_history]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketObservation":
        normalized = _normalize_legacy_data(data)
        normalized["price_history"] = [
            point if isinstance(point, PricePoint) else PricePoint(**point)
            for point in normalized.get("price_history", [])
        ]
        valid_fields = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in normalized.items() if key in valid_fields})


def _normalize_legacy_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    inference = normalized.pop("inference", {}) or {}
    scores = normalized.pop("scores", {}) or {}

    if "description_raw" not in normalized:
        normalized["description_raw"] = normalized.pop("raw_text", "")
    if "size_raw" not in normalized:
        normalized["size_raw"] = normalized.pop("size", "")
    if "brand_raw" not in normalized:
        normalized["brand_raw"] = normalized.pop("brand", "")

    normalized.setdefault("source_type", _legacy_source_type(normalized.get("source", "manual")))
    normalized.setdefault("inferred_size_category", _legacy_size_category(inference.get("size_category", "unknown")))
    normalized.setdefault("inferred_brand", inference.get("brand", "unknown"))
    normalized.setdefault("product_type", _legacy_product_type(inference.get("product_type", "other")))
    normalized.setdefault("target_sku_fit", _legacy_target_fit(inference.get("relevance_to_targets", "low"), normalized["inferred_size_category"]))
    normalized.setdefault("delivery_mentioned", inference.get("delivery_mentioned", False))
    normalized.setdefault("assembly_mentioned", inference.get("assembly_mentioned", False))
    normalized.setdefault("pickup_required", "transport required" in inference.get("pain_points", []))
    normalized.setdefault("permit_or_placement_mentions", False)
    normalized.setdefault("search_keyword", "")
    normalized.setdefault("thumbnail_url", "")
    normalized.setdefault("image_urls", [])
    normalized.setdefault("posted_time", "")
    normalized.setdefault("source_metadata", {})
    normalized.setdefault("llm_analysis", {})
    normalized.setdefault("llm_content_hash", "")
    normalized.setdefault("analysis_quality", "fallback_only")
    normalized.setdefault("last_seen", normalized.get("date_seen", date.today().isoformat()))
    normalized.setdefault("price_history", _initial_price_history(normalized))
    normalized.setdefault("extraction_notes", [])
    normalized.setdefault("demand_relevance_score", scores.get("demand_relevance", 1))
    normalized.setdefault("price_attractiveness_score", scores.get("price_attractiveness", 1))
    normalized.setdefault("local_competitive_signal_score", scores.get("local_competitive_signal", 1))
    normalized.setdefault("delivery_assembly_gap_score", scores.get("delivery_assembly_opportunity", 1))
    normalized.setdefault("overall_signal_score", 1.0)
    normalized.setdefault("score_notes", scores.get("notes", []))
    normalized.setdefault("change_notes", [])
    normalized.setdefault("retailer", "")
    normalized.setdefault("product_title", normalized.get("title", ""))
    normalized.setdefault("rating", None)
    normalized.setdefault("review_count", None)
    normalized.setdefault("delivery_available", normalized.get("delivery_mentioned", False))
    normalized.setdefault("delivery_cost_if_known", "")
    normalized.setdefault("assembly_service_available", normalized.get("assembly_mentioned", False))
    normalized.setdefault("return_policy_notes", "")
    normalized.setdefault("warranty_notes", "")
    normalized.setdefault("fetch_status", "")
    normalized.setdefault("verification_status", "unverified")
    normalized.setdefault("demand_match", "unknown")
    normalized.setdefault("false_positive_risk", "unknown")
    normalized.setdefault("evidence_quality", "unknown")
    normalized.setdefault("learning_notes", [])
    return normalized


def _initial_price_history(data: dict[str, Any]) -> list[dict[str, Any]]:
    price = data.get("price")
    if price is None:
        return []
    return [{"price": price, "date_seen": data.get("date_seen", date.today().isoformat())}]


def _legacy_source_type(source: str) -> str:
    return source if source in SOURCE_TYPES else "manual"


def _legacy_size_category(value: str) -> str:
    if value == "4x6 horizontal":
        return "4x6_horizontal"
    if value == "6x5 vertical":
        return "6x5_vertical"
    return value or "unknown"


def _legacy_product_type(value: str) -> str:
    return value.replace(" ", "_")


def _legacy_target_fit(relevance: str, size_category: str) -> str:
    if size_category in {"4x6_horizontal", "6x5_vertical"}:
        return size_category
    if relevance in {"direct", "adjacent", "weak"}:
        return "adjacent_expansion"
    return "not_relevant"
