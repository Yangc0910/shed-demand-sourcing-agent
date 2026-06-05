from __future__ import annotations

from collections import Counter

from shed_agent.models import MarketObservation


def format_candidate_verification_section(observations: list[MarketObservation]) -> list[str]:
    local = [item for item in observations if item.is_local_demand_source]
    counts = Counter(item.verification_status for item in local)
    match_counts = Counter(item.demand_match for item in local)
    likely_noise = [
        item
        for item in local
        if item.verification_status == "likely_noise"
        or item.demand_match in {"noise", "retail_like_or_partner_listing"}
        or item.false_positive_risk == "high"
    ]
    uncertain = [item for item in local if item.verification_status == "watch_uncertain"]

    lines = [
        "## Candidate Verification / Learning",
        f"- Verification status counts: {_format_counter(counts)}",
        f"- Demand match counts: {_format_counter(match_counts)}",
        "- Interpretation: search results are candidate signals; verified/uncertain/noise labels help prevent false positives from driving demand.",
    ]

    lines.extend(["", "### Likely Noise / False Positive Watch"])
    if likely_noise:
        for item in likely_noise[:10]:
            reason = "; ".join(item.learning_notes[:2]) or item.demand_match or "needs review"
            lines.append(f"- {item.title} ({item.location or 'unknown'}, {_money(item.price)}): {reason}")
    else:
        lines.append("- No likely-noise candidates flagged yet.")

    lines.extend(["", "### Watch-Uncertain Candidates"])
    if uncertain:
        for item in uncertain[:10]:
            note = "; ".join(item.learning_notes[:2]) or "plausible but needs detail/photo verification"
            lines.append(f"- {item.title} ({item.target_sku_fit}, {item.location or 'unknown'}, {_money(item.price)}): {note}")
    else:
        lines.append("- No uncertain candidates flagged yet.")
    return lines


def _format_counter(counter: Counter) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key or 'unknown'}: {value}" for key, value in counter.most_common())


def _money(value: float | None) -> str:
    return f"${value:.0f}" if value is not None else "unknown price"
