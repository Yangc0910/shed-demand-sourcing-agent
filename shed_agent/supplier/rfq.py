from __future__ import annotations

from shed_agent.supplier.config import SupplierConfig


PRODUCT_LABELS_EN = {
    "4x6_horizontal": "4 x 6 ft horizontal resin/plastic storage shed",
    "6x5_vertical": "6 x 5 ft vertical resin/plastic storage shed",
}
PRODUCT_LABELS_ZH = {
    "4x6_horizontal": "4 x 6 英尺卧式树脂/塑料储物棚",
    "6x5_vertical": "6 x 5 英尺立式树脂/塑料储物棚",
}


def generate_rfq_template(product_type: str, config: SupplierConfig | None = None) -> dict[str, str]:
    config = config or SupplierConfig()
    return {
        "english": generate_english_rfq(product_type, config),
        "chinese": generate_chinese_rfq(product_type, config),
    }


def generate_english_rfq(product_type: str, config: SupplierConfig) -> str:
    product = PRODUCT_LABELS_EN.get(product_type, "compact resin/plastic storage shed")
    tiers = " / ".join(str(value) for value in config.rfq_price_tiers)
    return f"""Hello,

We are evaluating suppliers for a small first inventory batch of {product} for local in-stock sales in the Boston, Massachusetts area. Our preferred first batch is {config.preferred_batch_min}-{config.preferred_batch_max} units, with a maximum of {config.maximum_initial_batch} units.

Please provide the following information:
1. Product model number, external dimensions, and internal dimensions.
2. Material: PP, HDPE, resin, or other.
3. Whether a floor is included.
4. UV resistance, weather resistance, and recommended outdoor conditions.
5. Packaging dimensions, gross weight, and net weight.
6. Number of cartons per unit.
7. MOQ.
8. Unit price tiers for {tiers} units.
9. Sample availability, sample cost, and sample lead time.
10. Production lead time.
11. Whether an English installation manual is available.
12. Whether an installation video is available.
13. Whether a spare parts package is available.
14. Your experience exporting this product or similar products to the United States.
15. Whether neutral packaging and neutral branding are available.
16. Estimated shipping cost and shipping terms to {config.destination}.
17. Whether the product is suitable for local delivery and homeowner assembly.

Please also share product photos, packaging photos, warranty or after-sales information, and any risks we should know about.

This is an information request only and is not a purchase commitment.

Thank you."""


def generate_chinese_rfq(product_type: str, config: SupplierConfig) -> str:
    product = PRODUCT_LABELS_ZH.get(product_type, "紧凑型树脂/塑料储物棚")
    tiers = " / ".join(str(value) for value in config.rfq_price_tiers)
    return f"""您好，

我们正在评估适合美国马萨诸塞州波士顿地区本地现货销售的{product}供应商。首批采购偏好为 {config.preferred_batch_min}-{config.preferred_batch_max} 套，最多 {config.maximum_initial_batch} 套。

请提供以下信息：
1. 产品型号、外部尺寸和内部尺寸。
2. 材料：PP、HDPE、树脂或其他材料。
3. 是否包含地板。
4. 抗紫外线、耐候性能以及建议的户外使用条件。
5. 包装尺寸、毛重和净重。
6. 每套产品的纸箱数量。
7. 最小起订量（MOQ）。
8. {tiers} 套的阶梯单价。
9. 是否可以提供样品、样品费用和样品交期。
10. 生产交期。
11. 是否可以提供英文安装说明书。
12. 是否可以提供安装视频。
13. 是否可以提供备件包。
14. 贵司向美国出口该产品或类似产品的经验。
15. 是否支持中性包装和中性品牌。
16. 运送到 {config.destination} 的预估运费和贸易条款。
17. 产品是否适合本地配送以及由家庭用户自行安装。

另外，请提供产品照片、包装照片、质保或售后信息，以及我们需要了解的任何风险。

此信息请求不构成采购承诺。

谢谢。"""
