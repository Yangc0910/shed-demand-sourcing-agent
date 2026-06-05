from __future__ import annotations

from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierConfidenceScore, SupplierThread
from shed_agent.supplier.risks import supplier_risk_checklist


def score_supplier_candidate(
    supplier: Supplier,
    product: ProductCandidate,
    thread: SupplierThread | None = None,
    config: SupplierConfig | None = None,
) -> SupplierConfidenceScore:
    config = config or SupplierConfig()
    categories = {
        "sku_fit": _sku_fit(product, config),
        "moq_fit": _moq_fit(product, config),
        "unit_economics": _unit_economics(product, config),
        "packaging_manageability": _packaging(product, config),
        "shipping_clarity": _shipping(product),
        "us_export_experience": _tri_state_score(supplier.us_export_experience),
        "english_manual": _tri_state_score(product.english_manual_available),
        "installation_video": _tri_state_score(product.installation_video_available),
        "spare_parts": _tri_state_score(product.spare_parts_available),
        "assembly_simplicity": _assembly(product),
        "quality_packaging_risk": _quality_risk(supplier, product, config),
        "supplier_responsiveness": _responsiveness(thread),
        "quote_completeness": _quote_completeness(product),
    }
    weights = {
        "sku_fit": 1.2,
        "moq_fit": 1.5,
        "unit_economics": 1.0,
        "packaging_manageability": 1.2,
        "shipping_clarity": 1.0,
        "us_export_experience": 0.8,
        "english_manual": 0.5,
        "installation_video": 0.4,
        "spare_parts": 0.8,
        "assembly_simplicity": 0.5,
        "quality_packaging_risk": 1.0,
        "supplier_responsiveness": 0.4,
        "quote_completeness": 1.2,
    }
    score = round(sum(categories[name] * weights[name] for name in categories) / sum(weights.values()), 1)
    score = _apply_score_gates(score, supplier, product, config)
    risks = supplier_risk_checklist(supplier, product, config)
    notes = [
        f"{name.replace('_', ' ').title()}: {value:.1f}/10"
        for name, value in categories.items()
    ]
    notes.extend(f"Risk: {risk}" for risk in risks[:5])
    return SupplierConfidenceScore(
        product_id=product.product_id,
        score=score,
        recommendation=_recommendation_with_gates(score, supplier, product, config),
        category_scores=categories,
        notes=notes,
    )


def recommendation_for_score(score: float, config: SupplierConfig | None = None) -> str:
    config = config or SupplierConfig()
    thresholds = config.score_thresholds
    if score >= thresholds.get("strongCandidate", 8.0):
        return "strong candidate"
    if score >= thresholds.get("watch", 6.0):
        return "watch"
    if score >= thresholds.get("needsMoreInfo", 4.0):
        return "needs more info"
    return "reject"


def _sku_fit(product: ProductCandidate, config: SupplierConfig) -> float:
    return 10 if product.product_type in config.target_product_types else 2


def _moq_fit(product: ProductCandidate, config: SupplierConfig) -> float:
    if product.moq is None:
        return 4
    if product.moq <= config.preferred_batch_max:
        return 10
    if product.moq <= config.maximum_initial_batch:
        return 8
    if product.moq <= 20:
        return 4
    return 1


def _unit_economics(product: ProductCandidate, config: SupplierConfig) -> float:
    if product.unit_price is None:
        return 4
    target = config.target_unit_costs.get(product.product_type)
    if not target:
        return 5
    ratio = product.unit_price / target
    if ratio <= 0.7:
        return 10
    if ratio <= 0.9:
        return 8
    if ratio <= 1.0:
        return 6
    if ratio <= 1.2:
        return 4
    return 2


def _packaging(product: ProductCandidate, config: SupplierConfig) -> float:
    if not product.carton_size or product.gross_weight is None or product.cartons_per_unit is None:
        return 4
    score = 10.0
    if product.gross_weight > config.manageable_gross_weight_kg:
        score -= 4
    if product.cartons_per_unit > config.manageable_cartons_per_unit:
        score -= 3
    if not product.packaging_notes:
        score -= 1
    return max(score, 1)


def _shipping(product: ProductCandidate) -> float:
    if product.estimated_shipping_cost is not None and product.shipping_terms:
        return 10
    if product.estimated_shipping_cost is not None or product.shipping_terms:
        return 6
    return 3


def _tri_state_score(value: str) -> float:
    candidate = str(value or "").strip().lower()
    if candidate.startswith("yes"):
        candidate = "yes"
    elif candidate.startswith("no"):
        candidate = "no"
    return {"yes": 10, "unknown": 4, "no": 1}.get(candidate, 4)


def _assembly(product: ProductCandidate) -> float:
    text = product.assembly_notes.lower()
    if any(term in text for term in ("easy", "simple", "homeowner", "two person", "2 person")):
        return 9
    if any(term in text for term in ("complex", "professional", "difficult")):
        return 3
    if product.english_manual_available == "yes" and product.installation_video_available == "yes":
        return 8
    return 4


def _quality_risk(supplier: Supplier, product: ProductCandidate, config: SupplierConfig) -> float:
    risk_count = len(supplier_risk_checklist(supplier, product, config))
    if risk_count <= 2:
        return 9
    if risk_count <= 5:
        return 7
    if risk_count <= 8:
        return 4
    return 2


def _responsiveness(thread: SupplierThread | None) -> float:
    if thread is None or not thread.messages:
        return 4
    inbound = sum(1 for message in thread.messages if message.direction == "inbound")
    outbound = sum(1 for message in thread.messages if message.direction in {"outbound_draft", "outbound_sent"})
    if inbound >= 2:
        return 9
    if inbound == 1:
        return 7
    if outbound:
        return 3
    return 4


def _quote_completeness(product: ProductCandidate) -> float:
    fields = [
        product.external_dimensions,
        product.internal_dimensions,
        product.material if product.material != "unknown" else "",
        product.unit_price,
        product.moq,
        product.price_tiers if all(str(tier) in product.price_tiers for tier in (5, 10, 20, 50)) else "",
        product.sample_cost,
        product.sample_lead_time,
        product.carton_size,
        product.gross_weight,
        product.cartons_per_unit,
        product.production_lead_time,
        product.english_manual_available if product.english_manual_available != "unknown" else "",
        product.installation_video_available if product.installation_video_available != "unknown" else "",
        product.spare_parts_available if product.spare_parts_available != "unknown" else "",
        product.shipping_terms,
    ]
    complete = sum(value is not None and value != "" for value in fields)
    return round(1 + 9 * complete / len(fields), 1)


def _apply_score_gates(
    score: float,
    supplier: Supplier,
    product: ProductCandidate,
    config: SupplierConfig,
) -> float:
    if product.product_type not in config.target_product_types:
        score = min(score, 3.9)
    if product.moq is not None and product.moq > config.maximum_initial_batch * 2:
        score = min(score, 3.5)
    if (
        supplier.us_export_experience == "no"
        and product.english_manual_available == "no"
        and product.spare_parts_available == "no"
    ):
        score = min(score, 3.5)
    return round(score, 1)


def _recommendation_with_gates(
    score: float,
    supplier: Supplier,
    product: ProductCandidate,
    config: SupplierConfig,
) -> str:
    if product.product_type not in config.target_product_types:
        return "reject"
    if product.moq is not None and product.moq > config.maximum_initial_batch * 2:
        return "reject"
    if (
        supplier.us_export_experience == "no"
        and product.english_manual_available == "no"
        and product.spare_parts_available == "no"
    ):
        return "reject"
    return recommendation_for_score(score, config)
