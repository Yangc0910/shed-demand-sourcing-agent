from __future__ import annotations

from datetime import date

from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.followup import generate_follow_up_plan
from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierMessageDraft, SupplierThread
from shed_agent.supplier.risks import supplier_risk_checklist
from shed_agent.supplier.rfq import generate_rfq_template
from shed_agent.supplier.scoring import score_supplier_candidate


RECOMMENDATION_ZH = {
    "strong candidate": "强候选",
    "watch": "持续观察",
    "needs more info": "需补充信息",
    "reject": "淘汰",
}
THREAD_STATUS_ZH = {
    "new": "新建",
    "draft_ready": "草稿待审核",
    "waiting_for_reply": "等待供应商回复",
    "reply_received": "已收到回复",
    "needs_follow_up": "需要追问",
    "closed": "已关闭",
    "archived": "已归档",
}
TRI_STATE_ZH = {"yes": "是", "no": "否", "unknown": "未知"}
PRODUCT_TYPE_ZH = {
    "4x6_horizontal": "4x6 卧式棚",
    "6x5_vertical": "6x5 立式棚",
    "deck_box": "储物箱",
    "accessory": "配件",
    "other": "其他",
}
MISSING_INFORMATION_ZH = {
    "external dimensions": "外部尺寸",
    "internal dimensions": "内部尺寸",
    "material": "材料",
    "floor included": "是否包含地板",
    "uv/weather resistance": "抗紫外线与耐候性",
    "unit price": "单价",
    "price tiers 5/10/20/50": "5/10/20/50 套阶梯价",
    "moq": "最小起订量",
    "sample": "样品费用与交期",
    "production lead time": "生产交期",
    "carton size": "包装箱尺寸",
    "gross weight": "毛重",
    "cartons per unit": "每套纸箱数量",
    "shipping": "运费与贸易条款",
    "english manual": "英文安装说明书",
    "installation video": "安装视频",
    "spare parts": "备件支持",
    "neutral branding": "中性包装与品牌",
    "warranty/after-sales": "质保与售后",
    "us export experience": "美国出口经验",
}
PURPOSE_ZH = {
    "initial_rfq": "初始询价",
    "follow_up": "信息追问",
    "pricing_clarification": "价格澄清",
    "sample_request": "样品请求",
    "shipping_request": "运费请求",
    "packaging_request": "包装信息请求",
    "spare_parts_request": "备件请求",
    "close_out": "结束沟通",
}


def generate_supplier_rfq_pack(
    suppliers: list[Supplier],
    products: list[ProductCandidate],
    threads: list[SupplierThread],
    drafts: list[SupplierMessageDraft],
    config: SupplierConfig | None = None,
) -> str:
    config = config or SupplierConfig()
    supplier_by_id = {item.supplier_id: item for item in suppliers}
    thread_by_supplier = {item.supplier_id: item for item in threads}
    scored = []
    for product in products:
        supplier = supplier_by_id.get(product.supplier_id)
        if supplier:
            scored.append((product, supplier, score_supplier_candidate(supplier, product, thread_by_supplier.get(supplier.supplier_id), config)))
    scored.sort(key=lambda item: item[2].score, reverse=True)

    lines = [
        f"# 供应商询价包 - {date.today().isoformat()}",
        "",
        "> 私有内部采购工作流。系统不会自动发送供应商消息，任何报价都不构成采购承诺。",
        "",
        "## 决策总览",
        _decision_summary_table(scored, thread_by_supplier, config),
        "",
        "## 供应商短名单",
    ]
    lines.extend(_supplier_shortlist(scored) or ["- 当前没有达到强候选或持续观察标准的供应商。"])
    lines.extend(["", "## 淘汰与暂缓候选", _pass_hold_section(scored, config)])
    lines.extend(["", "## 产品候选对比", _product_table(scored)])
    lines.extend(["", "## 供应商沟通状态", _thread_table(threads, supplier_by_id)])
    lines.extend(["", "## 最新报价摘要", _quote_details(scored)])
    lines.extend(["", "## 缺失信息", _missing_information(threads, products, supplier_by_id, config)])
    lines.extend(["", "## 建议追问", _follow_up_questions(threads, products, supplier_by_id, config)])
    lines.extend(["", "## 待审核消息草稿", _pending_drafts(drafts, supplier_by_id)])
    lines.extend(["", "## 价格与起订量对比", _price_table(scored)])
    lines.extend(["", "## 包装与重量对比", _packaging_table(scored)])
    lines.extend(["", "## 安装与支持准备度", _support_table(scored)])
    lines.extend(["", "## 风险检查清单", _risk_section(scored, config)])
    lines.extend(["", "## 供应商信心评分", _score_section(scored)])
    lines.extend(["", "## 候选建议", _recommendation_section(scored)])

    for product_type in config.target_product_types:
        templates = generate_rfq_template(product_type, config)
        lines.extend(
            [
                "",
                f"## 初始询价模板 - {_product_type_zh(product_type)}",
                "",
                "### 英文",
                "",
                templates["english"],
                "",
                "### 中文",
                "",
                templates["chinese"],
            ]
        )
    return "\n".join(lines) + "\n"


def _supplier_shortlist(scored) -> list[str]:
    seen: set[str] = set()
    lines: list[str] = []
    for product, supplier, score in scored:
        if score.recommendation not in {"strong candidate", "watch"}:
            continue
        if supplier.supplier_id in seen:
            continue
        seen.add(supplier.supplier_id)
        lines.append(
            f"- {supplier.supplier_name}（{supplier.platform}）："
            f"首选产品 {product.product_name}，评分 {score.score}/10，建议：{_recommendation_zh(score.recommendation)}。"
        )
    return lines


def _decision_summary_table(scored, thread_by_supplier: dict[str, SupplierThread], config: SupplierConfig) -> str:
    rows = [
        "| 供应商 | 产品 | 评分 | 建议 | 首批库存适配度 | 缺失项 | 下一步动作 |",
        "|---|---|---:|---|---|---:|---|",
    ]
    for product, supplier, score in scored:
        thread = thread_by_supplier.get(supplier.supplier_id)
        missing_count = len(generate_follow_up_plan(thread or SupplierThread(supplier_id=supplier.supplier_id), [product], supplier, config).missing_information)
        rows.append(
            f"| {_cell(supplier.supplier_name)} | {_cell(product.product_name)} | {score.score} | {_recommendation_zh(score.recommendation)} | "
            f"{_first_batch_fit(product, config)} | {missing_count} | {_cell(_next_action(score.recommendation, missing_count))} |"
        )
    return "\n".join(rows)


def _pass_hold_section(scored, config: SupplierConfig) -> str:
    lines = []
    for product, supplier, score in scored:
        if score.recommendation == "reject":
            lines.append(
                f"- 淘汰：{supplier.supplier_name} / {product.product_name}。"
                f"{_first_batch_fit(product, config)}；评分 {score.score}/10。"
            )
        elif score.recommendation == "needs more info":
            lines.append(
                f"- 暂缓：{supplier.supplier_name} / {product.product_name}。"
                f"在补齐报价、包装、运输和支持信息前不要推进。"
            )
    return "\n".join(lines) or "- 当前没有淘汰或暂缓候选。"


def _product_table(scored) -> str:
    rows = ["| 供应商 | 产品 | 类型 | 材料 | 外部尺寸 | 评分 |", "|---|---|---|---|---|---:|"]
    rows.extend(
        f"| {_cell(supplier.supplier_name)} | {_cell(product.product_name)} | {_product_type_zh(product.product_type)} | "
        f"{product.material} | {_cell(product.external_dimensions or '未知')} | {score.score} |"
        for product, supplier, score in scored
    )
    return "\n".join(rows)


def _thread_table(threads: list[SupplierThread], supplier_by_id: dict[str, Supplier]) -> str:
    rows = ["| 供应商 | 状态 | 最近收到回复 | 最近发送消息 | 下一步动作 |", "|---|---|---|---|---|"]
    rows.extend(
        f"| {_cell(supplier_by_id.get(thread.supplier_id).supplier_name if supplier_by_id.get(thread.supplier_id) else thread.supplier_id)} | "
        f"{_thread_status_zh(thread.thread_status)} | {thread.last_inbound_at or '-'} | {thread.last_outbound_at or '-'} | "
        f"{_cell(_next_action_text_zh(thread.recommended_next_action))} |"
        for thread in threads
    )
    return "\n".join(rows)


def _quote_details(scored) -> str:
    lines = []
    for product, supplier, _score in scored:
        lines.append(
            f"- {supplier.supplier_name} / {product.product_name}: "
            f"单价 {_money(product.unit_price, product.currency)}，MOQ {product.moq if product.moq is not None else '-'}，"
            f"外部尺寸 {product.external_dimensions or '-'}，包装箱 {product.carton_size or '-'}，"
            f"毛重 {product.gross_weight if product.gross_weight is not None else '-'}，"
            f"运输 {_shipping_summary(product)}。"
        )
    return "\n".join(lines) or "- 暂无已提取报价。"


def _missing_information(
    threads: list[SupplierThread],
    products: list[ProductCandidate],
    supplier_by_id: dict[str, Supplier],
    config: SupplierConfig,
) -> str:
    lines = []
    for thread in threads:
        thread_products = [item for item in products if item.product_id in thread.product_ids]
        supplier = supplier_by_id.get(thread.supplier_id)
        plan = generate_follow_up_plan(thread, thread_products, supplier, config)
        label = supplier.supplier_name if supplier else thread.supplier_id
        product_names = "、".join(item.product_name for item in thread_products) or "未关联产品的沟通线程"
        missing = "、".join(_missing_information_zh(item) for item in plan.missing_information) or "无"
        lines.append(f"- {label} / {product_names}：{missing}")
    return "\n".join(lines) or "- 暂无供应商沟通线程。"


def _follow_up_questions(
    threads: list[SupplierThread],
    products: list[ProductCandidate],
    supplier_by_id: dict[str, Supplier],
    config: SupplierConfig,
) -> str:
    lines = []
    for thread in threads:
        thread_products = [item for item in products if item.product_id in thread.product_ids]
        supplier = supplier_by_id.get(thread.supplier_id)
        plan = generate_follow_up_plan(thread, thread_products, supplier, config)
        if not plan.questions_chinese:
            continue
        label = supplier.supplier_name if supplier else thread.supplier_id
        lines.append(f"- {label}:")
        lines.extend(f"  {index}. {question}" for index, question in enumerate(plan.questions_chinese, 1))
    return "\n".join(lines) or "- 暂无建议追问。"


def _pending_drafts(drafts: list[SupplierMessageDraft], supplier_by_id: dict[str, Supplier]) -> str:
    pending = [item for item in drafts if item.approval_status == "pending"]
    lines = [
        f"- {supplier_by_id.get(item.supplier_id).supplier_name if supplier_by_id.get(item.supplier_id) else item.supplier_id}: "
        f"{_purpose_zh(item.purpose)}，草稿 ID：{item.draft_id}"
        for item in pending
    ]
    return "\n".join(lines) or "- 暂无待审核草稿。"


def _price_table(scored) -> str:
    rows = ["| 供应商 | 产品 | 单价 | MOQ | 5 / 10 / 20 / 50 套阶梯价 | 样品费用 | 预估运费 |", "|---|---|---:|---:|---|---:|---:|"]
    rows.extend(
        f"| {_cell(supplier.supplier_name)} | {_cell(product.product_name)} | {_money(product.unit_price, product.currency)} | "
        f"{product.moq if product.moq is not None else '-'} | {_price_tiers(product)} | {_money(product.sample_cost, product.currency)} | "
        f"{_money(product.estimated_shipping_cost, product.currency)} |"
        for product, supplier, _score in scored
    )
    return "\n".join(rows)


def _packaging_table(scored) -> str:
    rows = ["| 供应商 | 产品 | 包装箱尺寸 | 毛重 | 净重 | 每套纸箱数量 |", "|---|---|---|---:|---:|---:|"]
    rows.extend(
        f"| {_cell(supplier.supplier_name)} | {_cell(product.product_name)} | {_cell(product.carton_size or '-')} | "
        f"{product.gross_weight if product.gross_weight is not None else '-'} | {product.net_weight if product.net_weight is not None else '-'} | "
        f"{product.cartons_per_unit if product.cartons_per_unit is not None else '-'} |"
        for product, supplier, _score in scored
    )
    return "\n".join(rows)


def _support_table(scored) -> str:
    rows = ["| 供应商 | 产品 | 美国出口经验 | 英文说明书 | 安装视频 | 备件支持 | 中性品牌 |", "|---|---|---|---|---|---|---|"]
    rows.extend(
        f"| {_cell(supplier.supplier_name)} | {_cell(product.product_name)} | {_tri_state_zh(supplier.us_export_experience)} | {_tri_state_zh(product.english_manual_available)} | "
        f"{_tri_state_zh(product.installation_video_available)} | {_tri_state_zh(product.spare_parts_available)} | {_tri_state_zh(product.neutral_branding_available)} |"
        for product, supplier, _score in scored
    )
    return "\n".join(rows)


def _risk_section(scored, config: SupplierConfig) -> str:
    lines = []
    for product, supplier, _score in scored:
        risks = supplier_risk_checklist(supplier, product, config)
        risk_text = "；".join(_risk_notes_zh(risks)) or "未识别到主要检查清单风险"
        lines.append(f"- {supplier.supplier_name} / {product.product_name}：{risk_text}")
    return "\n".join(lines) or "- 暂无可评估候选。"


def _score_section(scored) -> str:
    return "\n".join(
        f"- {supplier.supplier_name} / {product.product_name}：{score.score}/10（{_recommendation_zh(score.recommendation)}）"
        for product, supplier, score in scored
    ) or "- 暂无评分。"


def _recommendation_section(scored) -> str:
    return "\n".join(
        f"- {supplier.supplier_name} / {product.product_name}：{_recommendation_zh(score.recommendation)}。"
        f"{_recommendation_rationale(score.recommendation)}"
        for product, supplier, score in scored
    ) or "- 暂无建议。"


def _money(value: float | None, currency: str) -> str:
    return f"{currency} {value:.2f}" if value is not None else "-"


def _cell(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ")


def _first_batch_fit(product: ProductCandidate, config: SupplierConfig) -> str:
    if product.moq is None:
        return "MOQ 未知"
    if product.moq <= config.preferred_batch_max:
        return "适合首选 6-8 套批量"
    if product.moq <= config.maximum_initial_batch:
        return "符合最多 10 套限制"
    return f"不适合首批库存；MOQ {product.moq}"


def _next_action(recommendation: str, missing_count: int) -> str:
    if recommendation == "strong candidate":
        return "确认样品与最终落地成本"
    if recommendation == "watch":
        return "补齐剩余信息"
    if recommendation == "needs more info":
        return f"针对 {missing_count} 个缺失项发送追问"
    return "暂不推进，除非供应商条款发生重大变化"


def _price_tiers(product: ProductCandidate) -> str:
    values = []
    for tier in ("5", "10", "20", "50"):
        value = product.price_tiers.get(tier)
        values.append(f"{tier}: {_money(value, product.currency)}" if value is not None else f"{tier}: -")
    return "<br>".join(values)


def _recommendation_rationale(recommendation: str) -> str:
    if recommendation == "strong candidate":
        return "继续沟通，验证样品，并在任何采购决定前确认最终落地成本。"
    if recommendation == "watch":
        return "保持活跃，但在推进前补齐报价与物流信息。"
    if recommendation == "needs more info":
        return "暂缓推进，等待针对性追问得到回复。"
    return "不适合作为首批 5-10 套库存供应商，除非供应商大幅调整条款。"


def _shipping_summary(product: ProductCandidate) -> str:
    cost = _money(product.estimated_shipping_cost, product.currency)
    terms = product.shipping_terms or ""
    return " ".join(value for value in (cost, terms) if value and value != "-") or "-"


def _recommendation_zh(value: str) -> str:
    return RECOMMENDATION_ZH.get(value, value)


def _thread_status_zh(value: str) -> str:
    return THREAD_STATUS_ZH.get(value, value)


def _tri_state_zh(value: str) -> str:
    return TRI_STATE_ZH.get(value, value)


def _product_type_zh(value: str) -> str:
    return PRODUCT_TYPE_ZH.get(value, value)


def _missing_information_zh(value: str) -> str:
    return MISSING_INFORMATION_ZH.get(value, value)


def _purpose_zh(value: str) -> str:
    return PURPOSE_ZH.get(value, value)


def _next_action_text_zh(value: str) -> str:
    translations = {
        "prepare initial RFQ": "准备初始询价",
        "review pending initial RFQ draft": "审核待发送的初始询价草稿",
        "review and approve a follow-up draft": "审核并批准追问草稿",
        "review pending follow-up draft": "审核待发送的追问草稿",
        "review quote and supplier confidence score": "审核报价与供应商信心评分",
        "wait for supplier reply": "等待供应商回复",
        "pass unless terms change materially": "暂不推进，除非供应商条款发生重大变化",
    }
    return translations.get(value, value)


def _risk_note_zh(value: str) -> str:
    exact = {
        "Product is not a target compact shed SKU.": "产品不属于目标紧凑型 shed SKU。",
        "External dimensions are missing.": "缺少外部尺寸。",
        "Internal dimensions are missing.": "缺少内部尺寸。",
        "Material is not confirmed.": "材料尚未确认。",
        "Floor inclusion is not confirmed.": "是否包含地板尚未确认。",
        "UV and weather resistance are not confirmed.": "抗紫外线与耐候性尚未确认。",
        "MOQ is missing.": "缺少最小起订量。",
        "Unit price is missing.": "缺少单价。",
        "Price tiers for 5 / 10 / 20 / 50 units are incomplete.": "5 / 10 / 20 / 50 套阶梯价不完整。",
        "Sample cost or sample lead time is unclear.": "样品费用或样品交期不明确。",
        "Carton dimensions are missing.": "缺少包装箱尺寸。",
        "Gross weight is missing.": "缺少毛重。",
        "Number of cartons per unit is missing.": "缺少每套纸箱数量。",
        "Shipping cost or shipping terms are unclear.": "运费或贸易条款不明确。",
        "Packaging protection and damage controls are unclear.": "包装防护与破损控制措施不明确。",
        "US export experience is unknown.": "美国出口经验未知。",
        "Supplier reports no US export experience.": "供应商表示没有美国出口经验。",
        "English installation manual is unavailable.": "无法提供英文安装说明书。",
        "Installation video is unavailable.": "无法提供安装视频。",
        "Spare parts support is unavailable.": "无法提供备件支持。",
        "Neutral packaging or branding is unavailable.": "无法提供中性包装或中性品牌。",
        "English installation manual is not confirmed.": "英文安装说明书尚未确认。",
        "Installation video is not confirmed.": "安装视频尚未确认。",
        "Spare parts support is not confirmed.": "备件支持尚未确认。",
        "Neutral packaging or branding is not confirmed.": "中性包装或品牌尚未确认。",
        "Warranty and after-sales support are unclear.": "质保与售后支持不明确。",
    }
    if value in exact:
        return exact[value]
    if value.startswith("MOQ of ") and "exceeds the maximum initial batch" in value:
        return value.replace("MOQ of ", "MOQ ").replace(" exceeds the maximum initial batch of ", "，超过首批库存上限 ").replace(".", "。")
    lower = value.lower()
    if "moq" in lower or "minimum order" in lower:
        return "MOQ 可能不适合首批小批量库存。"
    if "sample cost" in lower or "sample availability" in lower:
        return "样品费用、可用性或交期需要进一步确认。"
    if "shipping" in lower or "landed cost" in lower:
        return "运输成本或条款可能影响最终落地成本。"
    if "uv" in lower or "weather resistance" in lower or "durability" in lower:
        return "抗紫外线、耐候性或户外耐久性需要进一步确认。"
    if "lead time" in lower:
        return "交期可能影响库存准备时间。"
    if "warranty" in lower or "after sales" in lower or "after-sale" in lower:
        return "质保与售后支持需要进一步确认。"
    if "english manual" in lower or "installation video" in lower:
        return "安装说明与视频支持不足，可能影响客户安装体验。"
    if "spare parts" in lower:
        return "备件支持不足，可能增加售后风险。"
    if "export experience" in lower or "exported" in lower:
        return "美国出口经验需要进一步确认。"
    if "packaging" in lower or "weight" in lower or "dimensions" in lower:
        return "包装、重量或尺寸信息不足，可能影响物流评估。"
    if "neutral branding" in lower or "rebranding" in lower:
        return "中性品牌支持不足，可能限制品牌灵活性。"
    if "payment terms" in lower:
        return "付款条款需要进一步确认。"
    return value


def _risk_notes_zh(values: list[str]) -> list[str]:
    translated: list[str] = []
    for value in values:
        note = _risk_note_zh(value).rstrip("。.;；")
        if note and note not in translated:
            translated.append(note)
    return translated
