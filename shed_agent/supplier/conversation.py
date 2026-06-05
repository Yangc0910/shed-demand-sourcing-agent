from __future__ import annotations

from shed_agent.supplier.config import SupplierConfig
from shed_agent.supplier.followup import generate_follow_up_plan
from shed_agent.supplier.llm_extract import apply_extracted_fields, apply_supplier_extracted_fields, extract_supplier_reply
from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierThread, now_iso


def analyze_supplier_thread(
    thread: SupplierThread,
    products: list[ProductCandidate],
    supplier: Supplier | None = None,
    config: SupplierConfig | None = None,
) -> tuple[SupplierThread, list[ProductCandidate], Supplier | None, list[str]]:
    config = config or SupplierConfig()
    notes: list[str] = []
    relevant_products = [item for item in products if item.product_id in thread.product_ids]
    pending_messages = [
        message for message in thread.messages if message.direction == "inbound" and not message.extracted
    ]

    for message in pending_messages:
        extraction = extract_supplier_reply(message, relevant_products, config, supplier)
        target = _select_product(extraction.product_id, relevant_products)
        if target:
            apply_extracted_fields(target, extraction.extracted_fields)
            target.raw_quote_text = _append_quote_text(target.raw_quote_text, message.message_text)
            target.risk_notes = _merge_unique(target.risk_notes, extraction.risk_notes)
            target.updated_at = now_iso()
        if supplier:
            apply_supplier_extracted_fields(supplier, extraction.supplier_extracted_fields)
            supplier.updated_at = now_iso()
            if target and supplier.us_export_experience == "yes":
                target.risk_notes = [
                    note
                    for note in target.risk_notes
                    if not ("export" in note.lower() and ("unknown" in note.lower() or "no record" in note.lower()))
                ]
        message.extracted = True
        message.notes = f"Extraction quality: {extraction.analysis_quality}"
        thread.conversation_summary = extraction.conversation_summary or thread.conversation_summary
        thread.recommended_next_action = extraction.recommended_next_action or thread.recommended_next_action
        notes.append(f"Analyzed message {message.message_id} using {extraction.analysis_quality}.")

    plan = generate_follow_up_plan(thread, relevant_products, supplier, config)
    thread.missing_information = plan.missing_information
    thread.open_questions = plan.questions_english
    if thread.missing_information:
        thread.thread_status = "needs_follow_up"
        thread.recommended_next_action = "review and approve a follow-up draft"
        for product in relevant_products:
            product.follow_up_status = "needs_follow_up"
    elif pending_messages:
        thread.thread_status = "reply_received"
        thread.recommended_next_action = "review quote and supplier confidence score"
        for product in relevant_products:
            product.follow_up_status = "quote_complete"
    thread.updated_at = now_iso()
    return thread, products, supplier, notes


def _select_product(product_id: str, products: list[ProductCandidate]) -> ProductCandidate | None:
    if product_id:
        for product in products:
            if product.product_id == product_id:
                return product
    return products[0] if products else None


def _append_quote_text(existing: str, new_text: str) -> str:
    if not existing:
        return new_text
    if new_text in existing:
        return existing
    return f"{existing}\n\n--- Supplier reply ---\n{new_text}"


def _merge_unique(existing: list[str], new_items: list[str]) -> list[str]:
    merged = list(existing)
    for item in new_items:
        if item not in merged:
            merged.append(item)
    return merged
