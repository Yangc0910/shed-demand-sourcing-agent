from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from statistics import mean, median

from shed_agent.adjacent_watchlist import format_adjacent_watchlist
from shed_agent.config import AgentConfig
from shed_agent.decision import decision_check
from shed_agent.llm_analysis import generate_weekly_llm_synthesis
from shed_agent.models import MarketObservation
from shed_agent.retail_benchmark import format_retail_benchmark_section
from shed_agent.verification_report import format_candidate_verification_section


def generate_market_report(observations: list[MarketObservation], config: AgentConfig | None = None) -> str:
    config = config or AgentConfig()
    local_observations = [item for item in observations if item.is_local_demand_source]
    retail_observations = [item for item in observations if item.is_retail_comparable]
    supplier_observations = [item for item in observations if item.is_supplier_inventory_source]
    comparable_observations = [item for item in local_observations if item.is_useful_comparable]
    prices_by_category: dict[str, list[float]] = defaultdict(list)
    for item in comparable_observations:
        if item.price is not None:
            prices_by_category[item.inferred_size_category].append(item.price)

    brands = Counter(
        item.inferred_brand
        for item in local_observations
        if str(item.inferred_brand or "").strip() and item.inferred_brand != "unknown"
    )
    sizes = Counter(
        item.inferred_size_category
        for item in local_observations
        if str(item.inferred_size_category or "").strip() and item.inferred_size_category != "unknown"
    )
    status_counts = Counter(item.listing_status for item in local_observations)
    fast_moving = [item for item in comparable_observations if item.listing_status in {"sold", "disappeared"}]
    decision, reasons = decision_check(observations, config)
    llm_count = sum(1 for item in observations if item.analysis_quality in {"llm", "llm_cached"})
    fallback_count = sum(1 for item in observations if item.analysis_quality == "fallback_only")
    llm_synthesis = generate_weekly_llm_synthesis(local_observations, config)

    lines = [
        f"# Local Shed Market Report - {date.today().isoformat()}",
        "",
        "## Summary",
        f"- Local demand observations reviewed: {len(local_observations)}",
        f"- Retail benchmark observations reviewed: {len(retail_observations)}",
        f"- Supplier/inventory observations reviewed: {len(supplier_observations)}",
        f"- Useful local demand comparables: {len(comparable_observations)}",
        f"- Local listing statuses: {_format_counter(status_counts)}",
        f"- LLM-analyzed observations: {llm_count}",
        f"- Fallback-only observations: {fallback_count}",
        "- Source role note: local sources drive demand; retail sources only benchmark price/service; supplier sources are reserved for future inventory feasibility.",
    ]
    if llm_synthesis:
        lines.extend(
            [
                "",
                "## LLM Local Demand Synthesis",
                f"- Summary: {llm_synthesis.get('summary')}",
                f"- Products showing demand: {'; '.join(llm_synthesis.get('products_showing_demand', []))}",
                f"- Viable price bands: {'; '.join(llm_synthesis.get('viable_price_bands', []))}",
                f"- More promising target SKU: {llm_synthesis.get('more_promising_target_sku')}",
                f"- Delivery/assembly differentiator: {llm_synthesis.get('delivery_assembly_differentiator')}",
                f"- Adjacent categories emerging: {'; '.join(llm_synthesis.get('adjacent_categories_emerging', []))}",
                f"- LLM recommendation: {llm_synthesis.get('recommendation')}",
                f"- Supporting evidence: {'; '.join(llm_synthesis.get('supporting_evidence', []))}",
                f"- Missing evidence: {'; '.join(llm_synthesis.get('missing_evidence', []))}",
            ]
        )
    lines.extend(
        [
        "",
        "## Local Demand Signals",
        ]
    )

    if prices_by_category:
        for category, prices in sorted(prices_by_category.items()):
            lines.append(
                f"- {category}: count {len(prices)}, average ${mean(prices):.0f}, "
                f"median ${median(prices):.0f}, range ${min(prices):.0f}-${max(prices):.0f}"
            )
    else:
        lines.append("- No priced local comparable observations yet.")

    delivery_count = sum(1 for item in local_observations if item.delivery_mentioned)
    assembly_count = sum(1 for item in local_observations if item.assembly_mentioned)
    pickup_count = sum(1 for item in local_observations if item.pickup_required)
    target_observations = [item for item in local_observations if item.target_sku_fit in {"4x6_horizontal", "6x5_vertical"}]
    target_fast_moving = [
        item
        for item in target_observations
        if item.listing_status in {"sold", "disappeared"} or item.source_metadata.get("fast_moving_signal")
    ]
    target_pickup_gap = [item for item in target_observations if item.pickup_required and not item.delivery_mentioned]
    target_risk = [
        item
        for item in local_observations
        if item.source_metadata.get("missing_parts_or_damage_risk")
        or item.llm_analysis.get("missing_parts_risk") in {"medium", "high"}
        or item.llm_analysis.get("completeness_risk") in {"medium", "high"}
    ]

    lines.extend(
        [
            "",
            "## Common Brands And Sizes",
            f"- Local brands: {_format_counter(brands)}",
            f"- Local sizes/categories: {_format_counter(sizes)}",
            "",
            "## Delivery/Assembly Gap",
            f"- Local delivery mentioned count: {delivery_count}",
            f"- Local assembly/disassembly mentioned count: {assembly_count}",
            f"- Local pickup-required count: {pickup_count}",
            f"- Evidence for differentiation: {_delivery_gap_evidence(local_observations)}",
            "",
            "## Inventory Decision Signals",
            f"- Target compact shed observations: {len(target_observations)}",
            f"- Target listings with fast-moving/status interest signals: {len(target_fast_moving)}",
            f"- Target pickup-without-delivery gap count: {len(target_pickup_gap)}",
            f"- Listings with missing-parts/damage/completeness risk: {len(target_risk)}",
            "",
            "## Fast-Moving Listings",
        ]
    )
    lines.extend(
        [f"- {item.title} ({item.target_sku_fit}, {item.listing_status}, {_money(item.price)})" for item in fast_moving]
        or ["- None identified yet."]
    )

    lines.extend([""])
    lines.extend(format_candidate_verification_section(local_observations))

    lines.extend(["", "## Adjacent Backyard Opportunity Watchlist"])
    lines.extend(format_adjacent_watchlist(local_observations))

    lines.extend([""])
    lines.extend(format_retail_benchmark_section(observations, config))

    lines.extend(
        [
            "",
            "## Suggested Local Price Targets",
            f"- 4x6 horizontal shed: {_suggest_price('4x6_horizontal', prices_by_category.get('4x6_horizontal', []), config)}",
            f"- 6x5 vertical shed: {_suggest_price('6x5_vertical', prices_by_category.get('6x5_vertical', []), config)}",
            "",
            "## Recommendation",
            f"- Decision: {decision}",
        ]
    )
    lines.extend(f"- {reason}" for reason in reasons)
    lines.extend(
        [
            "",
            "## Risk Reminders",
            "- Quality, missing parts, packaging damage, storage space, assembly time, customer expectations, and returns remain key risks.",
            "- Buyer is responsible for confirming local zoning, HOA, setback, and permit requirements.",
        ]
    )
    return "\n".join(lines) + "\n"


def _format_counter(counter: Counter) -> str:
    if not counter:
        return "none observed"
    return ", ".join(f"{key}: {value}" for key, value in counter.most_common())


def _suggest_price(sku: str, prices: list[float], config: AgentConfig) -> str:
    fallback = config.provisional_target_prices.get(sku, 475 if sku == "4x6_horizontal" else 650)
    if len(prices) < 3:
        return (
            f"watch market; provisional target around ${fallback:.0f} "
            f"until at least 3 useful local comparables are observed"
        )
    observed_median = median(prices)
    target = round(max(observed_median * 1.12, observed_median + 50, fallback) / 10) * 10
    return f"consider ${target:.0f} based on observed median ${observed_median:.0f}"


def _delivery_gap_evidence(observations: list[MarketObservation]) -> str:
    if not observations:
        return "none observed"
    pickup = sum(1 for item in observations if item.pickup_required)
    no_delivery = sum(1 for item in observations if item.pickup_required and not item.delivery_mentioned)
    assembly = sum(1 for item in observations if item.assembly_mentioned)
    return f"{pickup} pickup-required listings, {no_delivery} pickup-without-delivery listings, {assembly} assembly/disassembly mentions"


def _money(value: float | None) -> str:
    return f"${value:.0f}" if value is not None else "unknown price"
