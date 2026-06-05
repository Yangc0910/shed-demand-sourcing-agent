from __future__ import annotations

from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.models import ProductCandidate, Supplier


def supplier_risk_checklist(
    supplier: Supplier,
    product: ProductCandidate,
    config: SupplierConfig | None = None,
) -> list[str]:
    config = config or SupplierConfig()
    risks: list[str] = []

    if product.product_type not in config.target_product_types:
        risks.append("Product is not a target compact shed SKU.")
    if not product.external_dimensions:
        risks.append("External dimensions are missing.")
    if not product.internal_dimensions:
        risks.append("Internal dimensions are missing.")
    if product.material == "unknown":
        risks.append("Material is not confirmed.")
    if product.has_floor == "unknown":
        risks.append("Floor inclusion is not confirmed.")
    if product.uv_weather_resistant == "unknown":
        risks.append("UV and weather resistance are not confirmed.")
    if product.moq is None:
        risks.append("MOQ is missing.")
    elif product.moq > config.maximum_initial_batch:
        risks.append(f"MOQ of {product.moq} exceeds the maximum initial batch of {config.maximum_initial_batch}.")
    if product.unit_price is None:
        risks.append("Unit price is missing.")
    if any(str(tier) not in product.price_tiers for tier in config.rfq_price_tiers):
        risks.append("Price tiers for 5 / 10 / 20 / 50 units are incomplete.")
    if product.sample_cost is None or not product.sample_lead_time:
        risks.append("Sample cost or sample lead time is unclear.")
    if not product.carton_size:
        risks.append("Carton dimensions are missing.")
    if product.gross_weight is None:
        risks.append("Gross weight is missing.")
    elif product.gross_weight > config.manageable_gross_weight_kg:
        risks.append("Gross weight may be difficult for local delivery and handling.")
    if product.cartons_per_unit is None:
        risks.append("Number of cartons per unit is missing.")
    elif product.cartons_per_unit > config.manageable_cartons_per_unit:
        risks.append("High carton count may increase handling and missing-parts risk.")
    if product.estimated_shipping_cost is None or not product.shipping_terms:
        risks.append("Shipping cost or shipping terms are unclear.")
    if not product.packaging_notes:
        risks.append("Packaging protection and damage controls are unclear.")
    if supplier.us_export_experience == "unknown":
        risks.append("US export experience is unknown.")
    elif supplier.us_export_experience == "no":
        risks.append("Supplier reports no US export experience.")
    _append_tri_state_risk(risks, product.english_manual_available, "English installation manual")
    _append_tri_state_risk(risks, product.installation_video_available, "Installation video")
    _append_tri_state_risk(risks, product.spare_parts_available, "Spare parts support")
    _append_tri_state_risk(risks, product.neutral_branding_available, "Neutral packaging or branding")
    if not product.warranty_or_after_sales_notes:
        risks.append("Warranty and after-sales support are unclear.")

    for note in product.risk_notes:
        if note not in risks:
            risks.append(note)
    return risks


def _append_tri_state_risk(risks: list[str], value: str, label: str) -> None:
    if value == "no":
        risks.append(f"{label} is unavailable.")
    elif value != "yes":
        risks.append(f"{label} is not confirmed.")
