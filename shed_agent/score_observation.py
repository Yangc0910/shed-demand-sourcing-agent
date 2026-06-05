from __future__ import annotations

from statistics import mean

from shed_agent.config import AgentConfig
from shed_agent.models import MarketObservation


DEFAULT_PRICE_BANDS = {
    "4x6_horizontal": (250, 550),
    "6x5_vertical": (350, 750),
    "adjacent_expansion": (75, 650),
}


def score_observation(observation: MarketObservation, config: AgentConfig | None = None) -> MarketObservation:
    if observation.analysis_quality in {"llm", "llm_cached"} and observation.llm_analysis:
        price = _score_price(observation, config)
        observation.price_attractiveness_score = price
        observation.overall_signal_score = round(
            mean(
                [
                    observation.demand_relevance_score,
                    observation.price_attractiveness_score,
                    observation.local_competitive_signal_score,
                    observation.delivery_assembly_gap_score,
                ]
            ),
            1,
        )
        return observation

    notes: list[str] = []
    demand = _score_demand_relevance(observation)
    demand = _adjust_for_verification(observation, demand)
    notes.append(f"Demand relevance {demand}/10 from target SKU fit '{observation.target_sku_fit}'.")

    price = _score_price(observation, config)
    if observation.price is None:
        notes.append("Price attractiveness 1/10 because no price was detected.")
    else:
        notes.append(f"Price attractiveness {price}/10 from detected price ${observation.price:.0f}.")

    competitive = _score_competitive_signal(observation)
    notes.append(f"Competitive signal {competitive}/10 from comparable fit, status, and price history.")

    delivery_gap = _score_delivery_assembly_gap(observation)
    notes.append(f"Delivery/assembly gap {delivery_gap}/10 from pickup, delivery, and assembly mentions.")

    overall = round(mean([demand, price, competitive, delivery_gap]), 1)
    observation.demand_relevance_score = demand
    observation.price_attractiveness_score = price
    observation.local_competitive_signal_score = competitive
    observation.delivery_assembly_gap_score = delivery_gap
    observation.overall_signal_score = overall
    observation.score_notes = notes
    return observation


def _score_demand_relevance(observation: MarketObservation) -> int:
    if observation.target_sku_fit in {"4x6_horizontal", "6x5_vertical"}:
        return 9
    if observation.target_sku_fit == "adjacent_expansion":
        return 5
    if observation.product_type == "large_shed":
        return 2
    return 1


def _adjust_for_verification(observation: MarketObservation, demand_score: int) -> int:
    if observation.verification_status == "likely_noise":
        return min(demand_score, 2)
    if observation.false_positive_risk == "high" and observation.demand_match in {
        "retail_like_or_partner_listing",
        "noise",
    }:
        return min(demand_score, 2)
    if observation.verification_status == "watch_uncertain" and observation.target_sku_fit in {
        "4x6_horizontal",
        "6x5_vertical",
    }:
        return min(demand_score, 8)
    return demand_score


def _score_price(observation: MarketObservation, config: AgentConfig | None) -> int:
    if observation.price is None:
        return 1
    target_fit = observation.target_sku_fit
    target_prices = config.provisional_target_prices if config else {}
    target_price = target_prices.get(target_fit)
    if target_price:
        if observation.price <= target_price * 0.75:
            return 9
        if observation.price <= target_price:
            return 7
        if observation.price <= target_price * 1.2:
            return 5
        return 2

    low, high = DEFAULT_PRICE_BANDS.get(target_fit, DEFAULT_PRICE_BANDS["adjacent_expansion"])
    midpoint = (low + high) / 2
    if low <= observation.price <= high:
        return 8 if observation.price <= midpoint else 6
    if observation.price < low:
        return 8
    return 3


def _score_competitive_signal(observation: MarketObservation) -> int:
    score = 2
    if observation.is_useful_comparable:
        score += 3
    if observation.source_metadata.get("fast_moving_signal"):
        score += 2
    if observation.listing_status in {"sold", "disappeared"}:
        score += 2
    elif observation.listing_status == "active":
        score += 1
    if len(observation.price_history) > 1:
        score += 1
    if observation.price is not None:
        score += 1
    return min(score, 10)


def _score_delivery_assembly_gap(observation: MarketObservation) -> int:
    score = 2
    if observation.pickup_required:
        score += 3
    if observation.assembly_mentioned:
        score += 2
    if not observation.delivery_mentioned and observation.pickup_required:
        score += 2
    if observation.delivery_mentioned:
        score += 1
    if observation.source_metadata.get("missing_parts_or_damage_risk"):
        score += 1
    return min(score, 10)
