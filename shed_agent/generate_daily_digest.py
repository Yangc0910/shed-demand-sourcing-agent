from __future__ import annotations

from datetime import date

from shed_agent.adjacent_watchlist import format_adjacent_watchlist
from shed_agent.config import AgentConfig
from shed_agent.decision import decision_check
from shed_agent.models import MarketObservation
from shed_agent.retail_benchmark import format_retail_benchmark_section
from shed_agent.verification_report import format_candidate_verification_section


def generate_daily_digest(observations: list[MarketObservation], config: AgentConfig) -> str:
    today = date.today().isoformat()
    local_observations = [item for item in observations if item.is_local_demand_source]
    retail_observations = [item for item in observations if item.is_retail_comparable]
    supplier_observations = [item for item in observations if item.is_supplier_inventory_source]
    recent = [item for item in local_observations if item.last_seen == today or item.date_seen == today]
    high_signal = sorted(
        [
            item
            for item in recent
            if item.target_sku_fit in {"4x6_horizontal", "6x5_vertical"}
            and (item.overall_signal_score >= 7 or item.target_sku_fit in {"4x6_horizontal", "6x5_vertical"})
        ],
        key=lambda item: item.overall_signal_score,
        reverse=True,
    )
    changed = [item for item in observations if item.change_notes]
    fast_interest = [
        item
        for item in recent
        if item.source_metadata.get("fast_moving_signal") or item.listing_status in {"sold", "disappeared"}
    ]
    pickup_count = sum(1 for item in recent if item.pickup_required)
    assembly_count = sum(1 for item in recent if item.assembly_mentioned)
    no_delivery_count = sum(1 for item in recent if item.pickup_required and not item.delivery_mentioned)
    decision, reasons = decision_check(observations, config)
    llm_count = sum(1 for item in observations if item.analysis_quality in {"llm", "llm_cached"})
    fallback_count = sum(1 for item in observations if item.analysis_quality == "fallback_only")

    lines = [
        "# Daily Shed Demand Digest",
        "",
        f"Date: {today}",
        "",
        "## Analysis Quality",
        f"- Local demand observations: {len(local_observations)}",
        f"- Retail benchmark observations: {len(retail_observations)}",
        f"- Supplier/inventory observations: {len(supplier_observations)}",
        f"- LLM-analyzed observations: {llm_count}",
        f"- Fallback-only observations: {fallback_count}",
        "- Source role note: local sources drive demand; retail sources only benchmark price/service; supplier sources are reserved for future inventory feasibility.",
        "",
        "## Local Demand Signals",
    ]
    if high_signal:
        for index, item in enumerate(high_signal[:10], start=1):
            lines.extend(
                [
                    f"{index}. {item.title or '(untitled listing)'}",
                    f"- Source: {item.source_type}",
                    f"- Price: {_money(item.price)}",
                    f"- Location: {item.location or 'unknown'}",
                    f"- Target SKU fit: {item.target_sku_fit}",
                    f"- Scores: demand {item.demand_relevance_score}/10, price {item.price_attractiveness_score}/10, gap {item.delivery_assembly_gap_score}/10, overall {item.overall_signal_score}/10",
                    f"- Recommended action: {item.llm_analysis.get('recommended_action', 'not available')}",
                    f"- Why it matters locally: {'; '.join(item.score_notes[:2])}",
                    "",
                ]
            )
    else:
        lines.append("- No new high-signal local listings today.")

    lines.extend(["", "## Notable Changes"])
    notable = []
    for item in changed[-10:]:
        notable.extend(f"- {item.title}: {note}" for note in item.change_notes[-2:])
    lines.extend(notable or ["- No notable price/status changes recorded."])

    lines.extend(["", "## Fast-Moving / Interest Signals"])
    lines.extend(
        [
            f"- {item.title}: {item.target_sku_fit}, {item.product_type}, {_money(item.price)}"
            for item in fast_interest[:10]
        ]
        or ["- No explicit just-listed, pending, sold, price-drop, likes/saves/comments, or high-interest signals detected today."]
    )

    risk_items = [
        item
        for item in recent
        if item.llm_analysis.get("missing_parts_risk") in {"medium", "high"}
        or item.llm_analysis.get("completeness_risk") in {"medium", "high"}
    ]
    lines.extend(["", "## High-Risk / Missing-Parts Watch"])
    lines.extend(
        [
            f"- {item.title}: missing parts risk {item.llm_analysis.get('missing_parts_risk')}, completeness risk {item.llm_analysis.get('completeness_risk')}"
            for item in risk_items[:10]
        ]
        or ["- No medium/high missing-parts or completeness risks flagged today."]
    )

    lines.extend([""])
    lines.extend(format_candidate_verification_section(recent))

    lines.extend(["", "## Adjacent Backyard Opportunity Watchlist"])
    lines.extend(format_adjacent_watchlist(recent))

    lines.extend([""])
    lines.extend(format_retail_benchmark_section(observations, config))

    lines.extend(
        [
            "",
            "## Delivery/Assembly Gap",
            f"- Local pickup required mentions today: {pickup_count}",
            f"- Local assembly/disassembly mentions today: {assembly_count}",
            f"- Local pickup without delivery today: {no_delivery_count}",
            "",
            "## Inventory Decision Signals",
            f"- Recommendation: {decision}",
        ]
    )
    lines.extend(f"- {reason}" for reason in reasons)
    return "\n".join(lines) + "\n"


def _money(value: float | None) -> str:
    return f"${value:.0f}" if value is not None else "unknown"
