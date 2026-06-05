from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows runtime
    winreg = None

from shed_agent.config import AgentConfig
from shed_agent.models import MarketObservation
from shed_agent.score_observation import score_observation
from shed_agent.storage import load_observations, save_observations


PRODUCT_TYPES = [
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
]
TARGET_SKU_FITS = ["4x6_horizontal", "6x5_vertical", "adjacent_expansion", "not_relevant"]


@dataclass
class LLMAnalysisRunSummary:
    enabled: bool = True
    analyzed: int = 0
    cache_hits: int = 0
    fallback: int = 0
    skipped_unchanged: int = 0
    errors: list[str] = field(default_factory=list)


LISTING_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "product_type",
        "target_sku_fit",
        "inferred_size_category",
        "inferred_brand",
        "condition_assessment",
        "completeness_risk",
        "stock_photo_risk",
        "delivery_mentioned",
        "pickup_required",
        "assembly_gap_signal",
        "missing_parts_risk",
        "permit_or_placement_relevance",
        "local_business_relevance",
        "adjacent_expansion_relevance",
        "buyer_seller_pain_points",
        "why_this_listing_matters",
        "risk_notes",
        "recommended_action",
        "local_demand_signal",
        "price_signal",
        "business_relevance_score",
        "delivery_assembly_opportunity_score",
        "inventory_learning_value_score",
        "adjacent_expansion_score",
        "rationale",
        "risks",
        "notes_for_weekly_report",
        "demand_match",
        "verification_status",
        "false_positive_risk",
        "evidence_quality",
        "learning_notes",
    ],
    "properties": {
        "product_type": {"type": "string", "enum": PRODUCT_TYPES},
        "target_sku_fit": {"type": "string", "enum": TARGET_SKU_FITS},
        "inferred_size_category": {"type": "string"},
        "inferred_brand": {"type": "string"},
        "condition_assessment": {
            "type": "string",
            "enum": ["new", "open_box", "used_good", "used_fair", "damaged", "incomplete", "unknown"],
        },
        "completeness_risk": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
        "stock_photo_risk": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
        "delivery_mentioned": {"type": "boolean"},
        "pickup_required": {"type": "boolean"},
        "assembly_gap_signal": {"type": "boolean"},
        "missing_parts_risk": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
        "permit_or_placement_relevance": {"type": "boolean"},
        "local_business_relevance": {"type": "string", "enum": ["low", "medium", "high"]},
        "adjacent_expansion_relevance": {"type": "string", "enum": ["none", "low", "medium", "high"]},
        "buyer_seller_pain_points": {"type": "array", "items": {"type": "string"}},
        "why_this_listing_matters": {"type": "string"},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
        "recommended_action": {
            "type": "string",
            "enum": [
                "ignore",
                "watch",
                "useful_comparable",
                "high_signal",
                "supplier_research_later",
                "first_inventory_candidate",
            ],
        },
        "local_demand_signal": {"type": "string", "enum": ["weak", "moderate", "strong"]},
        "price_signal": {"type": "string", "enum": ["low_price", "fair_price", "high_price", "unclear"]},
        "business_relevance_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "delivery_assembly_opportunity_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "inventory_learning_value_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "adjacent_expansion_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "rationale": {"type": "string"},
        "risks": {"type": "array", "items": {"type": "string"}},
        "notes_for_weekly_report": {"type": "string"},
        "demand_match": {
            "type": "string",
            "enum": [
                "target_candidate",
                "useful_local_comparable",
                "adjacent_opportunity",
                "retail_like_or_partner_listing",
                "noise",
                "uncertain",
            ],
        },
        "verification_status": {
            "type": "string",
            "enum": ["verified_signal", "watch_uncertain", "likely_noise"],
        },
        "false_positive_risk": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
        "evidence_quality": {
            "type": "string",
            "enum": ["actual_item_likely", "stock_photo_or_catalog_risk", "text_only", "insufficient"],
        },
        "learning_notes": {"type": "array", "items": {"type": "string"}},
    },
}


WEEKLY_SYNTHESIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "summary",
        "products_showing_demand",
        "viable_price_bands",
        "more_promising_target_sku",
        "delivery_assembly_differentiator",
        "adjacent_categories_emerging",
        "recommendation",
        "supporting_evidence",
        "missing_evidence",
    ],
    "properties": {
        "summary": {"type": "string"},
        "products_showing_demand": {"type": "array", "items": {"type": "string"}},
        "viable_price_bands": {"type": "array", "items": {"type": "string"}},
        "more_promising_target_sku": {"type": "string"},
        "delivery_assembly_differentiator": {"type": "string"},
        "adjacent_categories_emerging": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string", "enum": ["continue watching", "start supplier RFQ", "inventory candidate", "no-go"]},
        "supporting_evidence": {"type": "array", "items": {"type": "string"}},
        "missing_evidence": {"type": "array", "items": {"type": "string"}},
    },
}


def analyze_observations_with_llm(data_path: Path, config: AgentConfig) -> LLMAnalysisRunSummary:
    observations = load_observations(data_path)
    summary = LLMAnalysisRunSummary(enabled=config.enable_llm_analysis)
    if not config.enable_llm_analysis:
        return summary

    api_key_available = bool(_get_openai_api_key())
    if not api_key_available:
        summary.errors.append("OPENAI_API_KEY is not set")

    for observation in observations:
        content_hash = listing_content_hash(observation, config)
        if config.reanalyze_changed_listings_only and observation.llm_content_hash == content_hash and observation.llm_analysis:
            summary.skipped_unchanged += 1
            continue
        if (
            not api_key_available
            and config.reanalyze_changed_listings_only
            and observation.llm_content_hash == content_hash
            and observation.analysis_quality == "fallback_only"
        ):
            summary.skipped_unchanged += 1
            continue
        if summary.analyzed >= config.max_llm_listings_per_run:
            break

        cached = load_cached_listing_analysis(content_hash, config)
        if cached:
            apply_llm_analysis(observation, cached, content_hash, analysis_quality="llm_cached")
            summary.cache_hits += 1
            continue

        if not api_key_available:
            observation.analysis_quality = "fallback_only"
            observation.llm_content_hash = content_hash
            apply_fallback_verification(observation, config)
            _append_extraction_note_once(
                observation,
                "LLM analysis unavailable; deterministic fallback used: OPENAI_API_KEY is not set",
            )
            summary.fallback += 1
            continue

        try:
            analysis = call_openai_structured_json(
                model=config.llm_model,
                system_prompt=_listing_system_prompt(),
                user_prompt=_listing_user_prompt(observation, config),
                schema_name="shed_listing_analysis",
                schema=LISTING_ANALYSIS_SCHEMA,
            )
            save_cached_listing_analysis(content_hash, analysis, config)
            apply_llm_analysis(observation, analysis, content_hash, analysis_quality="llm")
            summary.analyzed += 1
        except Exception as exc:
            observation.analysis_quality = "fallback_only"
            observation.llm_content_hash = content_hash
            apply_fallback_verification(observation, config)
            _append_extraction_note_once(
                observation,
                f"LLM analysis unavailable; deterministic fallback used: {exc}",
            )
            summary.fallback += 1
            if str(exc) not in summary.errors:
                summary.errors.append(str(exc))

    save_observations([score_observation(item, config) for item in observations], data_path)
    return summary


def _append_extraction_note_once(observation: MarketObservation, note: str) -> None:
    if note not in observation.extraction_notes:
        observation.extraction_notes.append(note)


def generate_weekly_llm_synthesis(observations: list[MarketObservation], config: AgentConfig) -> dict[str, Any] | None:
    if not config.enable_llm_analysis:
        return None
    try:
        return call_openai_structured_json(
            model=config.llm_model,
            system_prompt=_weekly_system_prompt(),
            user_prompt=_weekly_user_prompt(observations, config),
            schema_name="shed_weekly_market_synthesis",
            schema=WEEKLY_SYNTHESIS_SCHEMA,
        )
    except Exception:
        return None


def apply_llm_analysis(
    observation: MarketObservation,
    analysis: dict[str, Any],
    content_hash: str,
    analysis_quality: str,
) -> None:
    observation.llm_analysis = analysis
    observation.llm_content_hash = content_hash
    observation.analysis_quality = analysis_quality
    observation.product_type = _normalize_product_type(analysis.get("product_type"), observation.product_type)
    observation.target_sku_fit = _normalize_target_sku_fit(analysis.get("target_sku_fit"), observation.target_sku_fit)
    observation.inferred_size_category = _normalize_free_text_label(
        analysis.get("inferred_size_category"),
        observation.inferred_size_category,
    )
    observation.inferred_brand = _normalize_free_text_label(analysis.get("inferred_brand"), observation.inferred_brand)
    observation.condition = _normalize_free_text_label(analysis.get("condition_assessment"), observation.condition)
    observation.delivery_mentioned = bool(analysis.get("delivery_mentioned", observation.delivery_mentioned))
    observation.pickup_required = bool(analysis.get("pickup_required", observation.pickup_required))
    observation.assembly_mentioned = bool(analysis.get("assembly_gap_signal", observation.assembly_mentioned))
    observation.permit_or_placement_mentions = bool(
        analysis.get("permit_or_placement_relevance", observation.permit_or_placement_mentions)
    )
    observation.demand_relevance_score = int(analysis.get("business_relevance_score", observation.demand_relevance_score))
    observation.delivery_assembly_gap_score = int(
        analysis.get("delivery_assembly_opportunity_score", observation.delivery_assembly_gap_score)
    )
    observation.local_competitive_signal_score = int(
        analysis.get("inventory_learning_value_score", observation.local_competitive_signal_score)
    )
    observation.overall_signal_score = round(
        (
            observation.demand_relevance_score
            + observation.price_attractiveness_score
            + observation.local_competitive_signal_score
            + observation.delivery_assembly_gap_score
        )
        / 4,
        1,
    )
    observation.score_notes = [
        f"LLM recommended action: {analysis.get('recommended_action', 'unknown')}.",
        analysis.get("rationale", ""),
        analysis.get("notes_for_weekly_report", ""),
    ]
    observation.demand_match = analysis.get("demand_match", observation.demand_match)
    observation.verification_status = analysis.get("verification_status", observation.verification_status)
    observation.false_positive_risk = analysis.get("false_positive_risk", observation.false_positive_risk)
    observation.evidence_quality = analysis.get("evidence_quality", observation.evidence_quality)
    observation.learning_notes = list(analysis.get("learning_notes", []))
    observation.source_metadata["verification"] = {
        "method": analysis_quality,
        "demand_match": observation.demand_match,
        "verification_status": observation.verification_status,
        "false_positive_risk": observation.false_positive_risk,
        "evidence_quality": observation.evidence_quality,
        "learning_notes": observation.learning_notes,
    }


def _normalize_free_text_label(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return fallback if str(fallback or "").strip() else "unknown"
    return candidate


def _normalize_product_type(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip()
    if candidate in PRODUCT_TYPES:
        return candidate
    return fallback if fallback in PRODUCT_TYPES else "other"


def _normalize_target_sku_fit(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip()
    if candidate in TARGET_SKU_FITS:
        return candidate
    return fallback if fallback in TARGET_SKU_FITS else "not_relevant"


def apply_fallback_verification(observation: MarketObservation, config: AgentConfig) -> None:
    text = f"{observation.title}\n{observation.location}\n{observation.description_raw}".lower()
    notes: list[str] = []
    demand_match = "uncertain"
    verification_status = "watch_uncertain"
    false_positive_risk = "medium"
    evidence_quality = "text_only"

    nonlocal_state = any(f", {state.lower()}" in text for state in ("ca", "tx", "fl", "ny", "nj", "pa", "oh"))
    if nonlocal_state and ", ma" not in text and "massachusetts" not in text:
        demand_match = "retail_like_or_partner_listing"
        verification_status = "likely_noise"
        false_positive_risk = "high"
        notes.append("Explicit non-local state detected; do not treat as local demand.")
    elif any(term in text for term in ("partner listing", "ships to you")):
        demand_match = "retail_like_or_partner_listing"
        verification_status = "likely_noise"
        false_positive_risk = "high"
        notes.append("Marketplace partner/catalog signal detected; use only as weak context.")
    elif observation.product_type == "other" and not any(term in text for term in ("shed", "deck box", "storage", "greenhouse")):
        demand_match = "noise"
        verification_status = "likely_noise"
        false_positive_risk = "high"
        notes.append("Visible text does not describe shed/storage demand.")
    elif observation.product_type == "shed_accessory":
        demand_match = "adjacent_opportunity"
        verification_status = "watch_uncertain"
        false_positive_risk = "medium"
        notes.append("Accessory signal; track separately and do not drive core shed demand.")
    elif observation.target_sku_fit in {"4x6_horizontal", "6x5_vertical"}:
        demand_match = "target_candidate"
        verification_status = "watch_uncertain"
        false_positive_risk = "medium"
        notes.append("Target-size candidate from visible text; needs detail/photo verification before high confidence.")
    elif observation.target_sku_fit == "adjacent_expansion":
        demand_match = "adjacent_opportunity"
        verification_status = "watch_uncertain"
        false_positive_risk = "medium"
        notes.append("Adjacent backyard/storage opportunity; preserve but do not drive core inventory decision.")

    if any(term in text for term in ("stock photo", "catalog", "rendering", "new in box", "ships")):
        evidence_quality = "stock_photo_or_catalog_risk"
        false_positive_risk = "high" if false_positive_risk != "low" else "medium"
        notes.append("Text suggests catalog/stock-photo risk; avoid over-weighting as local used demand.")

    observation.demand_match = demand_match
    observation.verification_status = verification_status
    observation.false_positive_risk = false_positive_risk
    observation.evidence_quality = evidence_quality
    observation.learning_notes = notes
    observation.source_metadata["verification"] = {
        "method": "fallback_verification",
        "demand_match": demand_match,
        "verification_status": verification_status,
        "false_positive_risk": false_positive_risk,
        "evidence_quality": evidence_quality,
        "learning_notes": notes,
    }


def listing_content_hash(observation: MarketObservation, config: AgentConfig) -> str:
    content = "\n".join(
        [
            observation.url,
            observation.title,
            str(observation.price),
            observation.location,
            observation.search_keyword,
            observation.description_raw[: config.max_description_chars_for_llm],
        ]
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_cached_listing_analysis(content_hash: str, config: AgentConfig) -> dict[str, Any] | None:
    if not config.cache_llm_results:
        return None
    path = Path(config.llm_cache_dir) / f"{content_hash}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_cached_listing_analysis(content_hash: str, analysis: dict[str, Any], config: AgentConfig) -> None:
    if not config.cache_llm_results:
        return
    path = Path(config.llm_cache_dir) / f"{content_hash}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")


def call_openai_structured_json(
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema_name: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    api_key = _get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc
    output_text = _extract_response_text(data)
    return json.loads(output_text)


def _get_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        return api_key
    if os.name != "nt" or winreg is None:
        return ""
    try:
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"Environment") as key:
                    value, _ = winreg.QueryValueEx(key, "OPENAI_API_KEY")
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            except OSError:
                continue
    except Exception:
        return ""
    return ""


def _extract_response_text(data: dict[str, Any]) -> str:
    if data.get("output_text"):
        return data["output_text"]
    chunks = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    if not chunks:
        raise RuntimeError("OpenAI response did not contain output text")
    return "".join(chunks)


def _listing_system_prompt() -> str:
    return (
        "You are a private local market analyst for compact outdoor resin/plastic sheds near Lexington MA. "
        "Return only JSON matching the schema. Keep the main inventory decision focused on 4x6 horizontal "
        "and 6x5 vertical sheds. Preserve adjacent backyard/storage opportunities separately. "
        "Treat Facebook search results as candidate signals, not proof of demand. Watch for false positives: "
        "partner/catalog listings, out-of-area results, accessories, unrelated goods, stock-photo-only clues, "
        "and listings that are merely retail availability rather than local marketplace demand. Do not over-filter: "
        "uncertain but plausible compact-shed listings should be marked watch_uncertain instead of discarded."
    )


def _listing_user_prompt(observation: MarketObservation, config: AgentConfig) -> str:
    context = {
        "target_skus": config.target_skus,
        "target_locations": config.target_locations,
        "title": observation.title,
        "price": observation.price,
        "location": observation.location,
        "url": observation.url,
        "source": observation.source,
        "source_type": observation.source_type,
        "search_keyword": observation.search_keyword,
        "raw_text": observation.description_raw[: config.max_description_chars_for_llm],
        "visible_metadata": observation.source_metadata,
    }
    return json.dumps(context, ensure_ascii=False)


def _weekly_system_prompt() -> str:
    return (
        "You synthesize a weekly local compact shed market report for a private local inventory experiment. "
        "Use evidence from observations. Do not recommend buying inventory without supplier landed cost confirmation."
    )


def _weekly_user_prompt(observations: list[MarketObservation], config: AgentConfig) -> str:
    compact = []
    for item in observations[-80:]:
        compact.append(
            {
                "title": item.title,
                "price": item.price,
                "location": item.location,
                "product_type": item.product_type,
                "target_sku_fit": item.target_sku_fit,
                "status": item.listing_status,
                "overall_signal_score": item.overall_signal_score,
                "delivery_assembly_gap_score": item.delivery_assembly_gap_score,
                "analysis_quality": item.analysis_quality,
                "llm_notes": item.llm_analysis.get("notes_for_weekly_report", ""),
            }
        )
    return json.dumps(
        {
            "target_skus": config.target_skus,
            "target_locations": config.target_locations,
            "observations": compact,
        },
        ensure_ascii=False,
    )
