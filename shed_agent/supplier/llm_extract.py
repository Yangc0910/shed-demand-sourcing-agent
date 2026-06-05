from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from shed_agent.llm_analysis import _get_openai_api_key, call_openai_structured_json
from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.followup import missing_product_information
from shed_agent.supplier.models import PRODUCT_TYPES, TRI_STATE_VALUES, ProductCandidate, Supplier, SupplierMessage, SupplierQuoteExtraction


QUOTE_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "product_id",
        "extracted_fields",
        "supplier_extracted_fields",
        "missing_information",
        "follow_up_questions",
        "risk_notes",
        "conversation_summary",
        "recommended_next_action",
    ],
    "properties": {
        "product_id": {"type": "string"},
        "extracted_fields": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "product_name",
                "product_type",
                "external_dimensions",
                "internal_dimensions",
                "material",
                "has_floor",
                "uv_weather_resistant",
                "color",
                "unit_price",
                "currency",
                "moq",
                "price_tiers",
                "sample_cost",
                "sample_lead_time",
                "production_lead_time",
                "carton_size",
                "gross_weight",
                "net_weight",
                "cartons_per_unit",
                "estimated_shipping_cost",
                "shipping_terms",
                "packaging_notes",
                "english_manual_available",
                "installation_video_available",
                "spare_parts_available",
                "neutral_branding_available",
                "warranty_or_after_sales_notes",
                "assembly_notes",
                "quote_date",
            ],
            "properties": {
                "product_name": {"type": ["string", "null"]},
                "product_type": {"enum": ["4x6_horizontal", "6x5_vertical", "deck_box", "accessory", "other", None]},
                "external_dimensions": {"type": ["string", "null"]},
                "internal_dimensions": {"type": ["string", "null"]},
                "material": {"type": ["string", "null"]},
                "has_floor": {"enum": ["yes", "no", "unknown", None]},
                "uv_weather_resistant": {"enum": ["yes", "no", "unknown", None]},
                "color": {"type": ["string", "null"]},
                "unit_price": {"type": ["number", "null"]},
                "currency": {"type": ["string", "null"]},
                "moq": {"type": ["integer", "null"]},
                "price_tiers": {
                    "type": ["object", "null"],
                    "additionalProperties": False,
                    "required": ["5", "10", "20", "50"],
                    "properties": {
                        "5": {"type": ["number", "null"]},
                        "10": {"type": ["number", "null"]},
                        "20": {"type": ["number", "null"]},
                        "50": {"type": ["number", "null"]},
                    },
                },
                "sample_cost": {"type": ["number", "null"]},
                "sample_lead_time": {"type": ["string", "null"]},
                "production_lead_time": {"type": ["string", "null"]},
                "carton_size": {"type": ["string", "null"]},
                "gross_weight": {"type": ["number", "null"]},
                "net_weight": {"type": ["number", "null"]},
                "cartons_per_unit": {"type": ["integer", "null"]},
                "estimated_shipping_cost": {"type": ["number", "null"]},
                "shipping_terms": {"type": ["string", "null"]},
                "packaging_notes": {"type": ["string", "null"]},
                "english_manual_available": {"enum": ["yes", "no", "unknown", None]},
                "installation_video_available": {"enum": ["yes", "no", "unknown", None]},
                "spare_parts_available": {"enum": ["yes", "no", "unknown", None]},
                "neutral_branding_available": {"enum": ["yes", "no", "unknown", None]},
                "warranty_or_after_sales_notes": {"type": ["string", "null"]},
                "assembly_notes": {"type": ["string", "null"]},
                "quote_date": {"type": ["string", "null"]},
            },
        },
        "supplier_extracted_fields": {
            "type": "object",
            "additionalProperties": False,
            "required": ["us_export_experience", "export_experience_notes"],
            "properties": {
                "us_export_experience": {"enum": ["yes", "no", "unknown", None]},
                "export_experience_notes": {"type": ["string", "null"]},
            },
        },
        "missing_information": {"type": "array", "items": {"type": "string"}},
        "follow_up_questions": {"type": "array", "items": {"type": "string"}},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
        "conversation_summary": {"type": "string"},
        "recommended_next_action": {"type": "string"},
    },
}


def extract_supplier_reply(
    message: SupplierMessage,
    products: list[ProductCandidate],
    config: SupplierConfig | None = None,
    supplier: Supplier | None = None,
) -> SupplierQuoteExtraction:
    config = config or SupplierConfig()
    content_hash = supplier_message_content_hash(message, products, supplier)
    cached = load_cached_extraction(content_hash, config)
    if cached:
        fallback = deterministic_extract_supplier_reply(message, products, content_hash, supplier)
        return _extraction_from_data(message.message_id, _merge_extraction_data(cached, fallback), content_hash, "llm_cached")

    if config.enable_llm_extraction and _get_openai_api_key():
        try:
            data = call_openai_structured_json(
                model=config.llm_model,
                system_prompt=_system_prompt(),
                user_prompt=_user_prompt(message, products, supplier),
                schema_name="supplier_quote_extraction",
                schema=QUOTE_EXTRACTION_SCHEMA,
            )
            fallback = deterministic_extract_supplier_reply(message, products, content_hash, supplier)
            merged = _merge_extraction_data(data, fallback)
            save_cached_extraction(content_hash, merged, config)
            return _extraction_from_data(message.message_id, merged, content_hash, "llm")
        except Exception:
            pass
    return deterministic_extract_supplier_reply(message, products, content_hash, supplier)


def deterministic_extract_supplier_reply(
    message: SupplierMessage,
    products: list[ProductCandidate],
    content_hash: str = "",
    supplier: Supplier | None = None,
) -> SupplierQuoteExtraction:
    text = message.message_text
    lower = text.lower()
    product = products[0] if products else None
    fields: dict[str, Any] = {}
    supplier_fields: dict[str, Any] = {}

    moq_match = re.search(r"(?:\bmoq\b|minimum order(?: quantity)?)\s*(?:is|:|=)?\s*(\d+)", lower)
    if moq_match:
        fields["moq"] = int(moq_match.group(1))
    price_match = re.search(r"(?:price(?: is)?\s*)?(?:usd|\$)\s*(\d+(?:\.\d+)?)\s*(?:per\s*(?:set|unit))?", lower)
    if price_match:
        fields["unit_price"] = float(price_match.group(1))
        fields["currency"] = "USD"
    price_tiers = {
        quantity: float(price)
        for quantity, price in re.findall(
            r"(\d+)\s*(?:sets?|units?)\s*[:=-]\s*(?:usd|\$)\s*(\d+(?:\.\d+)?)",
            lower,
        )
    }
    if price_tiers:
        fields["price_tiers"] = price_tiers
        if "10" in price_tiers:
            fields["unit_price"] = price_tiers["10"]
    external_match = re.search(r"external\s*(?:size|dimensions?)\s*[:=]\s*([^\n\r]+)", lower)
    if external_match:
        fields["external_dimensions"] = external_match.group(1).strip()
    elif re.search(r"\b\d+\s*x\s*\d+\s*ft\b", lower):
        fields["external_dimensions"] = re.search(r"\b\d+\s*x\s*\d+\s*ft\b", lower).group(0)
    internal_match = re.search(r"internal\s*(?:size|dimensions?)\s*[:=]\s*([^\n\r]+)", lower)
    if internal_match:
        fields["internal_dimensions"] = internal_match.group(1).strip()
    carton_match = re.search(r"(?:carton|package|packing)\s*(?:size|dimensions?)?\s*[:=]?\s*([\d.]+\s*[x×*]\s*[\d.]+\s*[x×*]\s*[\d.]+\s*(?:cm|mm|in)?)", lower)
    if carton_match:
        fields["carton_size"] = carton_match.group(1)
    gross_match = re.search(r"(?:gross weight|g\.?w\.?)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*kg", lower)
    if gross_match:
        fields["gross_weight"] = float(gross_match.group(1))
    net_match = re.search(r"(?:net weight|n\.?w\.?)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*kg", lower)
    if net_match:
        fields["net_weight"] = float(net_match.group(1))
    cartons_match = re.search(r"(\d+)\s*(?:cartons?|boxes?)\s*(?:per|/)\s*(?:unit|set)", lower)
    if cartons_match:
        fields["cartons_per_unit"] = int(cartons_match.group(1))
    if "hdpe" in lower:
        fields["material"] = "HDPE"
    elif re.search(r"\bpp\b", lower):
        fields["material"] = "PP"
    elif "resin" in lower:
        fields["material"] = "resin"

    fields["has_floor"] = _extract_tri_state(lower, ("floor included", "floor is included", "floor: included", "include floor", "with floor"), ("floor is not included", "without floor", "no floor"))
    fields["english_manual_available"] = _extract_tri_state(
        lower,
        ("english manual", "english installation manual", "manual in english"),
        ("do not have an english manual", "no english manual", "no english installation manual"),
    )
    fields["installation_video_available"] = _extract_tri_state(lower, ("installation video", "assembly video"), ("do not provide an installation video", "no installation video"))
    fields["spare_parts_available"] = _extract_tri_state(lower, ("spare parts", "replacement parts"), ("no spare parts", "do not provide spare parts"))
    fields["neutral_branding_available"] = _extract_tri_state(lower, ("neutral packaging", "neutral branding", "no-logo branding", "no logo branding"), ("neutral branding is not available", "no neutral branding"))
    fields["uv_weather_resistant"] = _extract_tri_state(lower, ("uv-resistant", "uv resistant", "weather resistant", "weatherproof"), ("not uv resistant", "not weather resistant"))
    fields = {key: value for key, value in fields.items() if value is not None and value != "" and value != "unknown"}

    sample_cost_match = re.search(r"sample cost\s*(?:is|:|=)?\s*(?:usd|\$)\s*(\d+(?:\.\d+)?)", lower)
    if sample_cost_match:
        fields["sample_cost"] = float(sample_cost_match.group(1))
    sample_lead_match = re.search(r"sample lead time\s*(?:is|:|=)?\s*([^\n\r.]+)", lower)
    if sample_lead_match:
        fields["sample_lead_time"] = sample_lead_match.group(1).strip()
    production_match = re.search(r"production lead time\s*(?:is|:|=)?\s*([^\n\r.]+)", lower)
    if production_match:
        fields["production_lead_time"] = production_match.group(1).strip()
    shipping_match = re.search(r"(?:estimated )?shipping cost[^\n\r]*?(?:usd|\$)\s*([\d,]+(?:\.\d+)?)", lower)
    if shipping_match:
        fields["estimated_shipping_cost"] = float(shipping_match.group(1).replace(",", ""))
    terms_match = re.search(r"\b(ddp|fob|cif|exw)\b(?:\s+terms?)?", lower)
    if terms_match:
        fields["shipping_terms"] = terms_match.group(1).upper()
    if "reinforced export cartons" in lower:
        fields["packaging_notes"] = "Reinforced export cartons with corner protection" if "corner protection" in lower else "Reinforced export cartons"
    elif "packing is large" in lower:
        fields["packaging_notes"] = "Supplier states packing is large; final carton dimensions and gross weight are not available."
    if "homeowner assembly" in lower:
        fields["assembly_notes"] = "Homeowner assembly is suitable for two adults" if "two adults" in lower else "Suitable for homeowner assembly"
    if "warranty" in lower or "after-sales" in lower:
        warranty_match = re.search(r"([^\n\r.]*warranty[^\n\r.]*(?:replacement parts|after-sales)?[^\n\r.]*)", text, re.IGNORECASE)
        fields["warranty_or_after_sales_notes"] = warranty_match.group(1).strip() if warranty_match else "Warranty or after-sales support mentioned"

    if re.search(r"(?:not exported|no .*export experience)[^\n\r]*(?:united states|u\.s\.|usa)", lower):
        supplier_fields["us_export_experience"] = "no"
        supplier_fields["export_experience_notes"] = "Supplier states no export experience for this product to the United States."
    elif re.search(r"(?:exported|export experience)[^\n\r]*(?:united states|u\.s\.|usa)", lower):
        supplier_fields["us_export_experience"] = "yes"
        supplier_fields["export_experience_notes"] = "Supplier states experience exporting this product or similar products to the United States."

    if product:
        preview = ProductCandidate.from_dict(product.to_dict())
        apply_extracted_fields(preview, fields)
        missing = missing_product_information(preview)
        product_id = product.product_id
    else:
        missing = ["product candidate"]
        product_id = ""
    return SupplierQuoteExtraction(
        message_id=message.message_id,
        product_id=product_id,
        extracted_fields=fields,
        supplier_extracted_fields=supplier_fields,
        missing_information=missing,
        follow_up_questions=[],
        risk_notes=[],
        conversation_summary="Supplier reply captured. Deterministic extraction used; review the original text and extracted fields.",
        recommended_next_action="review extraction and prepare follow-up",
        analysis_quality="fallback_only",
        content_hash=content_hash,
    )


def apply_extracted_fields(product: ProductCandidate, fields: dict[str, Any]) -> ProductCandidate:
    valid_fields = product.__dataclass_fields__.keys()
    for key, value in fields.items():
        if key not in valid_fields or value is None or value == "":
            continue
        if key == "product_type" and value not in PRODUCT_TYPES:
            continue
        if key in {
            "has_floor",
            "uv_weather_resistant",
            "english_manual_available",
            "installation_video_available",
            "spare_parts_available",
            "neutral_branding_available",
        }:
            value = _normalize_tri_state(value)
        if key == "price_tiers" and isinstance(value, dict):
            value = {str(tier): float(price) for tier, price in value.items() if price is not None}
        setattr(product, key, value)
    return product


def apply_supplier_extracted_fields(supplier: Supplier, fields: dict[str, Any]) -> Supplier:
    if fields.get("us_export_experience") in TRI_STATE_VALUES:
        supplier.us_export_experience = fields["us_export_experience"]
    if fields.get("export_experience_notes"):
        supplier.export_experience_notes = str(fields["export_experience_notes"])
    return supplier


def supplier_message_content_hash(
    message: SupplierMessage,
    products: list[ProductCandidate],
    supplier: Supplier | None = None,
) -> str:
    product_context = "\n".join(f"{item.product_id}|{item.product_name}|{item.product_type}" for item in products)
    supplier_context = f"{supplier.supplier_id}|{supplier.us_export_experience}" if supplier else ""
    return hashlib.sha256(f"{message.message_text}\n{product_context}\n{supplier_context}".encode("utf-8")).hexdigest()


def load_cached_extraction(content_hash: str, config: SupplierConfig) -> dict[str, Any] | None:
    if not config.cache_llm_results:
        return None
    path = Path(config.llm_cache_dir) / f"{content_hash}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_cached_extraction(content_hash: str, data: dict[str, Any], config: SupplierConfig) -> None:
    if not config.cache_llm_results:
        return
    path = Path(config.llm_cache_dir) / f"{content_hash}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _extraction_from_data(message_id: str, data: dict[str, Any], content_hash: str, quality: str) -> SupplierQuoteExtraction:
    return SupplierQuoteExtraction(
        message_id=message_id,
        product_id=data.get("product_id", ""),
        extracted_fields=data.get("extracted_fields", {}),
        supplier_extracted_fields=data.get("supplier_extracted_fields", {}),
        missing_information=data.get("missing_information", []),
        follow_up_questions=data.get("follow_up_questions", []),
        risk_notes=data.get("risk_notes", []),
        conversation_summary=data.get("conversation_summary", ""),
        recommended_next_action=data.get("recommended_next_action", ""),
        analysis_quality=quality,
        content_hash=content_hash,
    )


def _merge_extraction_data(data: dict[str, Any], fallback: SupplierQuoteExtraction) -> dict[str, Any]:
    merged = dict(data)
    merged["extracted_fields"] = _merge_fields(data.get("extracted_fields", {}), fallback.extracted_fields)
    merged["supplier_extracted_fields"] = _merge_fields(
        data.get("supplier_extracted_fields", {}),
        fallback.supplier_extracted_fields,
    )
    merged["risk_notes"] = _merge_unique(data.get("risk_notes", []), fallback.risk_notes)
    return merged


def _merge_fields(primary: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary)
    for key, value in fallback.items():
        current = merged.get(key)
        if key == "price_tiers" and isinstance(value, dict):
            tiers = dict(current) if isinstance(current, dict) else {}
            for tier, price in value.items():
                if tiers.get(tier) is None:
                    tiers[tier] = price
            merged[key] = tiers
        elif current is None or current == "" or current == "unknown":
            merged[key] = value
    return merged


def _merge_unique(primary: list[str], fallback: list[str]) -> list[str]:
    merged = list(primary)
    for item in fallback:
        if item not in merged:
            merged.append(item)
    return merged


def _system_prompt() -> str:
    return (
        "You extract structured supplier quote information for compact resin/plastic sheds. "
        "Return only JSON matching the schema. Do not invent values. Use null when information is absent. "
        "Keep yes/no/unknown fields limited to yes, no, or unknown. Identify risks and missing details needed "
        "to evaluate a small 6-8 unit first inventory batch, with 10 units maximum."
    )


def _user_prompt(message: SupplierMessage, products: list[ProductCandidate], supplier: Supplier | None) -> str:
    return json.dumps(
        {
            "supplier_reply": message.message_text,
            "supplier": supplier.to_dict() if supplier else None,
            "product_candidates": [item.to_dict() for item in products],
        },
        ensure_ascii=False,
    )


def _extract_tri_state(text: str, positive_terms: tuple[str, ...], negative_terms: tuple[str, ...]) -> str:
    if any(term in text for term in negative_terms):
        return "no"
    if any(term in text for term in positive_terms):
        return "yes"
    return "unknown"


def _normalize_tri_state(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in TRI_STATE_VALUES:
        return candidate
    if candidate.startswith("yes"):
        return "yes"
    if candidate.startswith("no"):
        return "no"
    return "unknown"
