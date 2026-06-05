from __future__ import annotations

from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierFollowUpPlan, SupplierThread


FIELD_QUESTIONS = {
    "external dimensions": (
        "Please confirm the product model and external dimensions.",
        "请确认产品型号和外部尺寸。",
    ),
    "internal dimensions": ("Please provide the usable internal dimensions.", "请提供产品可用的内部尺寸。"),
    "material": ("Please confirm whether the material is PP, HDPE, resin, or another material.", "请确认材料是 PP、HDPE、树脂还是其他材料。"),
    "floor included": ("Please confirm whether the floor is included.", "请确认是否包含地板。"),
    "uv/weather resistance": ("Please describe the UV and weather resistance.", "请说明产品的抗紫外线和耐候性能。"),
    "unit price": ("Please provide the current unit price.", "请提供当前单价。"),
    "price tiers 5/10/20/50": ("Please provide unit prices for 5, 10, 20, and 50 units.", "请提供 5、10、20 和 50 套的阶梯单价。"),
    "moq": ("Please confirm the MOQ.", "请确认最小起订量（MOQ）。"),
    "sample": ("Please confirm sample availability, sample cost, and sample lead time.", "请确认是否可提供样品、样品费用和样品交期。"),
    "production lead time": ("Please confirm the production lead time.", "请确认生产交期。"),
    "carton size": ("Please provide carton dimensions for one unit.", "请提供每套产品的包装箱尺寸。"),
    "gross weight": ("Please provide gross weight and net weight.", "请提供毛重和净重。"),
    "cartons per unit": ("Please confirm the number of cartons per unit.", "请确认每套产品的纸箱数量。"),
    "shipping": ("Please provide estimated shipping cost and shipping terms to Boston / East Coast US.", "请提供运送到美国波士顿/美国东海岸的预估运费和贸易条款。"),
    "english manual": ("Please confirm whether an English installation manual is available.", "请确认是否可以提供英文安装说明书。"),
    "installation video": ("Please confirm whether an installation video is available.", "请确认是否可以提供安装视频。"),
    "spare parts": ("Please confirm whether a spare parts package is available.", "请确认是否可以提供备件包。"),
    "neutral branding": ("Please confirm whether neutral packaging and branding are available.", "请确认是否支持中性包装和中性品牌。"),
    "warranty/after-sales": ("Please describe warranty and after-sales support.", "请说明质保和售后支持。"),
    "us export experience": (
        "Please confirm whether you have exported this product or similar products to the United States.",
        "请确认贵司是否向美国出口过该产品或类似产品。",
    ),
}


def missing_product_information(
    product: ProductCandidate,
    config: SupplierConfig | None = None,
) -> list[str]:
    config = config or SupplierConfig()
    missing: list[str] = []
    if not product.external_dimensions:
        missing.append("external dimensions")
    if not product.internal_dimensions:
        missing.append("internal dimensions")
    if product.material == "unknown":
        missing.append("material")
    if product.has_floor == "unknown":
        missing.append("floor included")
    if product.uv_weather_resistant == "unknown":
        missing.append("uv/weather resistance")
    if product.unit_price is None:
        missing.append("unit price")
    if any(str(tier) not in product.price_tiers for tier in config.rfq_price_tiers):
        missing.append("price tiers 5/10/20/50")
    if product.moq is None:
        missing.append("moq")
    if product.sample_cost is None or not product.sample_lead_time:
        missing.append("sample")
    if not product.production_lead_time:
        missing.append("production lead time")
    if not product.carton_size:
        missing.append("carton size")
    if product.gross_weight is None:
        missing.append("gross weight")
    if product.cartons_per_unit is None:
        missing.append("cartons per unit")
    if product.estimated_shipping_cost is None or not product.shipping_terms:
        missing.append("shipping")
    if product.english_manual_available == "unknown":
        missing.append("english manual")
    if product.installation_video_available == "unknown":
        missing.append("installation video")
    if product.spare_parts_available == "unknown":
        missing.append("spare parts")
    if product.neutral_branding_available == "unknown":
        missing.append("neutral branding")
    if not product.warranty_or_after_sales_notes:
        missing.append("warranty/after-sales")
    return missing


def missing_supplier_information(supplier: Supplier | None) -> list[str]:
    if supplier is None or supplier.us_export_experience == "unknown":
        return ["us export experience"]
    return []


def generate_follow_up_plan(
    thread: SupplierThread,
    products: list[ProductCandidate],
    supplier: Supplier | None = None,
    config: SupplierConfig | None = None,
) -> SupplierFollowUpPlan:
    config = config or SupplierConfig()
    missing: list[str] = []
    for product in products:
        for item in missing_product_information(product, config):
            if item not in missing:
                missing.append(item)
    for item in missing_supplier_information(supplier):
        if item not in missing:
            missing.append(item)
    english = [FIELD_QUESTIONS[item][0] for item in missing if item in FIELD_QUESTIONS]
    chinese = [FIELD_QUESTIONS[item][1] for item in missing if item in FIELD_QUESTIONS]
    return SupplierFollowUpPlan(
        thread_id=thread.thread_id,
        purpose=_purpose_for_missing(missing),
        missing_information=missing,
        questions_english=english,
        questions_chinese=chinese,
        rationale="Request the highest-value missing quote details before evaluating a first inventory batch.",
    )


def _purpose_for_missing(missing: list[str]) -> str:
    if any(item in missing for item in ("unit price", "price tiers 5/10/20/50", "moq")):
        return "pricing_clarification"
    if any(item in missing for item in ("shipping",)):
        return "shipping_request"
    if any(item in missing for item in ("carton size", "gross weight", "cartons per unit")):
        return "packaging_request"
    if any(item in missing for item in ("spare parts",)):
        return "spare_parts_request"
    return "follow_up"
