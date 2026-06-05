from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from shed_agent.config import AgentConfig
from shed_agent.models import MarketObservation


def decision_check(observations: list[MarketObservation], config: AgentConfig) -> tuple[str, list[str]]:
    retail_count = sum(1 for item in observations if item.is_retail_comparable)
    recent = [
        item
        for item in _last_n_days(observations, 30)
        if not item.is_retail_comparable and _is_local_market_observation(item, config)
    ]
    comparables = [item for item in recent if item.is_useful_comparable]
    target_fit = [item for item in recent if item.target_sku_fit in {"4x6_horizontal", "6x5_vertical"}]
    decision_pool = target_fit or comparables
    avg_overall = mean([item.overall_signal_score for item in decision_pool]) if decision_pool else 0
    avg_gap = mean([item.delivery_assembly_gap_score for item in decision_pool]) if decision_pool else 0
    fast_moving = [item for item in target_fit if item.listing_status in {"sold", "disappeared"}]
    thresholds = config.score_thresholds

    reasons = [
        f"{len(recent)} local marketplace observations in the last 30 days; core decision excludes {retail_count} retail benchmark observations and explicit non-local results.",
        f"{len(comparables)} useful comparables and {len(target_fit)} target-SKU-fit observations.",
        f"Average overall signal score is {avg_overall:.1f}; average delivery/assembly gap is {avg_gap:.1f}.",
        f"Fast-moving target comparables: {len(fast_moving)}.",
    ]

    if len(recent) < thresholds.get("continueWatchingMinimumObservations", 10):
        return "continue watching", reasons + ["Observation volume is still below the configured confidence floor."]

    if (
        len(comparables) >= thresholds.get("supplierRfqComparableCount30d", 10)
        or len(target_fit) >= thresholds.get("supplierRfqTargetFitCount30d", 5)
    ) and avg_overall >= thresholds.get("supplierRfqAverageOverallSignal", 7) and avg_gap >= thresholds.get("supplierRfqDeliveryGap", 6):
        return "start supplier RFQ", reasons + ["Thresholds support supplier discovery, but not purchasing."]

    if _inventory_candidate(target_fit, fast_moving, avg_overall, avg_gap, config):
        return "inventory candidate", reasons + ["Demand and service-gap signals look promising; landed cost still needs confirmation."]

    if _no_go(recent):
        return "no-go", reasons + ["Signals are mostly low relevance or weak price space."]

    return "continue watching", reasons + ["Signals are mixed or price bands are not clear enough yet."]


def _last_n_days(observations: list[MarketObservation], days: int) -> list[MarketObservation]:
    cutoff = date.today() - timedelta(days=days)
    recent = []
    for item in observations:
        try:
            if date.fromisoformat(item.date_seen) >= cutoff:
                recent.append(item)
        except ValueError:
            recent.append(item)
    return recent


def _inventory_candidate(
    target_fit: list[MarketObservation],
    fast_moving: list[MarketObservation],
    avg_overall: float,
    avg_gap: float,
    config: AgentConfig,
) -> bool:
    thresholds = config.score_thresholds
    return (
        len(target_fit) >= 5
        and bool(fast_moving)
        and avg_overall >= thresholds.get("inventoryCandidateAverageOverallSignal", 7.5)
        and avg_gap >= thresholds.get("inventoryCandidateDeliveryGap", 7)
    )


def _no_go(observations: list[MarketObservation]) -> bool:
    core_related = [
        item
        for item in observations
        if item.product_type
        in {
            "horizontal_shed",
            "vertical_shed",
            "large_shed",
            "bike_storage",
        }
        and item.demand_match not in {"noise", "retail_like_or_partner_listing"}
    ]
    if len(core_related) < 20:
        return False
    target = [item for item in core_related if item.target_sku_fit in {"4x6_horizontal", "6x5_vertical"}]
    avg_price = mean([item.price_attractiveness_score for item in target]) if target else 0
    return len(target) / len(core_related) < 0.15 or avg_price <= 3


def _is_local_market_observation(observation: MarketObservation, config: AgentConfig) -> bool:
    text = f"{observation.location} {observation.description_raw} {observation.title}".lower()
    nonlocal_state_match = any(f", {state.lower()}" in text for state in ("CA", "TX", "FL", "NY", "NJ", "PA", "OH"))
    if nonlocal_state_match and ", ma" not in text and "massachusetts" not in text:
        return False
    if ", ma" in text or "massachusetts" in text:
        return True
    if any(location.lower() in text for location in config.target_locations):
        return True
    return not observation.location
