from __future__ import annotations

from collections import defaultdict
from statistics import median

from shed_agent.config import AgentConfig
from shed_agent.models import MarketObservation


TARGET_SKUS = {"4x6_horizontal", "6x5_vertical"}


def format_retail_benchmark_section(observations: list[MarketObservation], config: AgentConfig) -> list[str]:
    retail = [item for item in observations if item.is_retail_comparable and item.fetch_status != "blocked"]
    blocked = [item for item in observations if item.is_retail_comparable and item.fetch_status == "blocked"]
    local = [item for item in observations if item.is_local_demand_source]
    lines = ["## Retail Benchmark"]
    if not retail and not blocked:
        lines.append("- No retail benchmark observations recorded yet.")
        return lines

    if retail:
        lines.extend(["", "### Price Range By Retailer"])
        by_retailer: dict[str, list[float]] = defaultdict(list)
        for item in retail:
            if item.price is not None:
                by_retailer[item.retailer or item.source].append(item.price)
        if by_retailer:
            for retailer, prices in sorted(by_retailer.items()):
                lines.append(f"- {retailer}: {len(prices)} priced item(s), range {_money(min(prices))}-{_money(max(prices))}, median {_money(median(prices))}")
        else:
            lines.append("- Retail products recorded, but no prices parsed yet.")

        lines.extend(["", "### Target SKU Retail References"])
        for sku in ("4x6_horizontal", "6x5_vertical"):
            sku_retail = [item for item in retail if item.target_sku_fit == sku and item.price is not None]
            if sku_retail:
                prices = [item.price for item in sku_retail if item.price is not None]
                lines.append(f"- {sku}: new retail benchmark {_money(min(prices))}-{_money(max(prices))}, median {_money(median(prices))}")
            else:
                fallback = config.provisional_target_prices.get(sku)
                fallback_text = f"; provisional target {_money(fallback)}" if fallback else ""
                lines.append(f"- {sku}: no new-retail benchmark parsed yet{fallback_text}")

        lines.extend(["", "### Local Used Vs New Retail Gap"])
        for sku in ("4x6_horizontal", "6x5_vertical"):
            lines.append(_gap_line(sku, local, retail, config))

        delivery_count = sum(1 for item in retail if item.delivery_available or item.delivery_mentioned)
        assembly_count = sum(1 for item in retail if item.assembly_service_available or item.assembly_mentioned)
        lines.extend(
            [
                "",
                "### Delivery / Assembly Benchmark",
                f"- Retail delivery available/mentioned: {delivery_count}",
                f"- Retail assembly service available/mentioned: {assembly_count}",
                f"- Differentiation note: {_differentiation_note(local, retail)}",
            ]
        )

    if blocked:
        lines.extend(["", "### Blocked Retail Pages"])
        lines.extend(f"- {item.retailer or item.source}: {item.url} recorded as blocked; no bypass attempted." for item in blocked[:10])
    return lines


def _gap_line(sku: str, local: list[MarketObservation], retail: list[MarketObservation], config: AgentConfig) -> str:
    local_prices = [item.price for item in local if item.target_sku_fit == sku and item.price is not None]
    retail_prices = [item.price for item in retail if item.target_sku_fit == sku and item.price is not None]
    if not local_prices or not retail_prices:
        target = config.provisional_target_prices.get(sku)
        return f"- {sku}: gap unclear; suggested local in-stock range needs more local and retail observations. Current provisional target: {_money(target)}"
    local_median = median(local_prices)
    retail_median = median(retail_prices)
    gap = retail_median - local_median
    lower = max(local_median + 40, retail_median * 0.78)
    upper = max(lower + 30, retail_median * 0.92)
    return (
        f"- {sku}: local used median {_money(local_median)} vs new retail median {_money(retail_median)} "
        f"(gap {_money(gap)}). Suggested local in-stock range {_money(lower)}-{_money(upper)}."
    )


def _differentiation_note(local: list[MarketObservation], retail: list[MarketObservation]) -> str:
    local_pickup_gap = sum(1 for item in local if item.pickup_required and not item.delivery_mentioned)
    retail_delivery = sum(1 for item in retail if item.delivery_available or item.delivery_mentioned)
    retail_assembly = sum(1 for item in retail if item.assembly_service_available or item.assembly_mentioned)
    if local_pickup_gap and (retail_delivery or retail_assembly):
        return "Local pickup friction plus retail delivery/assembly options suggests service expectations matter; local delivery/placement may still differentiate on speed and convenience."
    if local_pickup_gap:
        return "Local used listings show pickup friction; retail service availability needs more benchmarks."
    if retail_delivery or retail_assembly:
        return "Retailers mention delivery/assembly; compare against local in-stock speed and backyard placement convenience."
    return "No strong retail delivery/assembly benchmark yet."


def _money(value: float | None) -> str:
    return f"${value:.0f}" if value is not None else "unknown"
