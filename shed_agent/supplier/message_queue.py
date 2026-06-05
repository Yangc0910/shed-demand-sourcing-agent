from __future__ import annotations

import json
from typing import Protocol

from shed_agent.llm_analysis import _get_openai_api_key, call_openai_structured_json
from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.models import SupplierFollowUpPlan, SupplierMessageDraft, now_iso
from shed_agent.supplier.rfq import generate_rfq_template


class SupplierMessagingAdapter(Protocol):
    """Future outbound adapter contract. No live adapter is implemented in Phase 2A."""

    def send(self, draft: SupplierMessageDraft) -> str: ...


MESSAGE_DRAFT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["draft_text_chinese", "draft_text_english"],
    "properties": {
        "draft_text_chinese": {"type": "string"},
        "draft_text_english": {"type": "string"},
    },
}


def build_initial_rfq_draft(
    thread_id: str,
    supplier_id: str,
    product_type: str,
    config: SupplierConfig | None = None,
) -> SupplierMessageDraft:
    config = config or SupplierConfig()
    templates = generate_rfq_template(product_type, config)
    return SupplierMessageDraft(
        thread_id=thread_id,
        supplier_id=supplier_id,
        purpose="initial_rfq",
        draft_text_chinese=templates["chinese"],
        draft_text_english=templates["english"],
    )


def build_follow_up_draft(
    plan: SupplierFollowUpPlan,
    supplier_name: str = "",
    config: SupplierConfig | None = None,
) -> SupplierMessageDraft:
    config = config or SupplierConfig()
    llm_draft = _generate_llm_follow_up(plan, supplier_name, config)
    if llm_draft:
        return SupplierMessageDraft(
            thread_id=plan.thread_id,
            supplier_id="",
            purpose=plan.purpose,
            draft_text_english=llm_draft["draft_text_english"],
            draft_text_chinese=llm_draft["draft_text_chinese"],
        )
    greeting_en = f"Hello {supplier_name}," if supplier_name else "Hello,"
    greeting_zh = f"{supplier_name} 您好，" if supplier_name else "您好，"
    english_questions = "\n".join(f"{index}. {question}" for index, question in enumerate(plan.questions_english, 1))
    chinese_questions = "\n".join(f"{index}. {question}" for index, question in enumerate(plan.questions_chinese, 1))
    return SupplierMessageDraft(
        thread_id=plan.thread_id,
        supplier_id="",
        purpose=plan.purpose,
        draft_text_english=(
            f"{greeting_en}\n\nThank you for the information. Please help us confirm the following details:\n"
            f"{english_questions}\n\nThis is an information request only and is not a purchase commitment.\n\nThank you."
        ),
        draft_text_chinese=(
            f"{greeting_zh}\n\n感谢您提供的信息。请协助确认以下内容：\n"
            f"{chinese_questions}\n\n此信息请求不构成采购承诺。\n\n谢谢。"
        ),
    )


def _generate_llm_follow_up(
    plan: SupplierFollowUpPlan,
    supplier_name: str,
    config: SupplierConfig,
) -> dict[str, str] | None:
    if not config.enable_llm_drafting or not _get_openai_api_key():
        return None
    try:
        return call_openai_structured_json(
            model=config.llm_model,
            system_prompt=(
                "Draft a concise professional supplier follow-up in Chinese and English. "
                "Ask only the supplied questions. Do not make a purchase commitment, promise pricing, "
                "or imply that an order has been approved. Use a short greeting, one sentence of context, "
                "a numbered list of questions, and a short closing. Use a natural Chinese business tone and "
                "avoid compressing many questions into one dense sentence."
            ),
            user_prompt=json.dumps(
                {
                    "supplier_name": supplier_name,
                    "purpose": plan.purpose,
                    "questions_english": plan.questions_english,
                    "questions_chinese": plan.questions_chinese,
                    "rationale": plan.rationale,
                },
                ensure_ascii=False,
            ),
            schema_name="supplier_follow_up_draft",
            schema=MESSAGE_DRAFT_SCHEMA,
        )
    except Exception:
        return None


def approve_message_draft(draft: SupplierMessageDraft) -> SupplierMessageDraft:
    if draft.approval_status not in {"pending", "rejected"}:
        raise ValueError(f"Draft cannot be approved from status {draft.approval_status}.")
    draft.approval_status = "approved"
    draft.updated_at = now_iso()
    return draft


def reject_message_draft(draft: SupplierMessageDraft) -> SupplierMessageDraft:
    if draft.approval_status == "sent_manually":
        raise ValueError("A manually sent draft cannot be rejected.")
    draft.approval_status = "rejected"
    draft.updated_at = now_iso()
    return draft


def mark_message_sent_manually(draft: SupplierMessageDraft) -> SupplierMessageDraft:
    if draft.approval_status != "approved":
        raise ValueError("Draft must be approved before it can be marked as sent manually.")
    draft.approval_status = "sent_manually"
    draft.updated_at = now_iso()
    return draft
