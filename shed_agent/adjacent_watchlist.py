from __future__ import annotations

from shed_agent.models import MarketObservation


def adjacent_opportunities(observations: list[MarketObservation], limit: int = 10) -> list[MarketObservation]:
    return sorted(
        [item for item in observations if item.is_adjacent_expansion],
        key=lambda item: (item.overall_signal_score, item.delivery_assembly_gap_score),
        reverse=True,
    )[:limit]


def format_adjacent_watchlist(observations: list[MarketObservation]) -> list[str]:
    items = adjacent_opportunities(observations)
    if not items:
        return ["- No adjacent backyard opportunities captured yet."]

    lines: list[str] = []
    for item in items:
        lines.extend(
            [
                f"- {item.title or '(untitled adjacent item)'} ({_money(item.price)})",
                f"  Source: {item.source_type}",
                f"  Observed interest signal: {_interest_signal(item)}",
                f"  Product type: {item.product_type}",
                f"  Why it may matter: {_why_it_matters(item)}",
                f"  Risks: {_risks(item)}",
                f"  Delivery/assembly differentiator: {_delivery_differentiator(item)}",
                f"  Suggested action: {_suggested_action(item)}",
            ]
        )
    return lines


def _money(value: float | None) -> str:
    return f"${value:.0f}" if value is not None else "unknown price"


def _interest_signal(item: MarketObservation) -> str:
    text = f"{item.description_raw} {' '.join(item.change_notes)} {item.posted_time}".lower()
    signals = []
    for term in ("just listed", "listed today", "high interest", "popular", "views", "saves", "likes", "comments"):
        if term in text:
            signals.append(term)
    if item.listing_status in {"sold", "disappeared"}:
        signals.append(f"fast disappearance/status: {item.listing_status}")
    return ", ".join(signals) if signals else "not visible"


def _why_it_matters(item: MarketObservation) -> str:
    if item.product_type == "garden_dome":
        return "possible backyard comfort/season-extension product with assembly and transport friction."
    if item.product_type == "greenhouse":
        return "adjacent outdoor storage/garden demand that may share supplier and delivery economics."
    if item.product_type == "canopy_gazebo":
        return "backyard structure demand may reveal local delivery and setup willingness."
    if item.product_type in {"deck_box", "patio_storage", "bike_storage"}:
        return "compact storage adjacency that can inform future accessory or smaller-item strategy."
    if item.product_type == "shed_accessory":
        return "could support future accessory bundles after core shed demand is validated."
    return "adjacent backyard/storage signal worth preserving for future product strategy."


def _risks(item: MarketObservation) -> str:
    risks = {
        "garden_dome": "quality, completeness, wind/snow durability, missing parts, and assembly complexity.",
        "greenhouse": "wind/snow durability, panel damage, missing hardware, and anchoring expectations.",
        "canopy_gazebo": "weather durability, anchoring, fabric wear, and customer expectation risk.",
        "shed_accessory": "compatibility with stocked shed models and low standalone margin.",
    }
    return risks.get(item.product_type, "fit, condition, completeness, transport, and future supplier economics.")


def _delivery_differentiator(item: MarketObservation) -> str:
    if item.pickup_required or item.assembly_mentioned or not item.delivery_mentioned:
        return "yes, local delivery/placement/assembly may reduce buyer friction."
    return "possible, but no clear service gap was visible."


def _suggested_action(item: MarketObservation) -> str:
    if item.product_type in {"garden_dome", "greenhouse", "canopy_gazebo"} and item.overall_signal_score >= 6:
        return "watch / research suppliers later"
    if item.product_type in {"deck_box", "patio_storage", "bike_storage", "shed_accessory"}:
        return "watch"
    return "ignore unless repeated local signals appear"
