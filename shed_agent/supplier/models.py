from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


TRI_STATE_VALUES = {"yes", "no", "unknown"}
SUPPLIER_PLATFORMS = {"Alibaba", "Made-in-China", "1688", "Global Sources", "email", "other"}
SUPPLIER_STATUSES = {"new", "contacted", "replied", "waiting", "strong_candidate", "rejected", "archived"}
PRODUCT_TYPES = {"4x6_horizontal", "6x5_vertical", "deck_box", "accessory", "other"}
THREAD_STATUSES = {"new", "draft_ready", "waiting_for_reply", "reply_received", "needs_follow_up", "closed", "archived"}
MESSAGE_DIRECTIONS = {"inbound", "outbound_draft", "outbound_sent"}
APPROVAL_STATUSES = {"pending", "approved", "rejected", "sent_manually", "archived"}
MESSAGE_PURPOSES = {
    "initial_rfq",
    "follow_up",
    "pricing_clarification",
    "sample_request",
    "shipping_request",
    "packaging_request",
    "spare_parts_request",
    "close_out",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Supplier:
    supplier_name: str
    platform: str = "other"
    supplier_url: str = ""
    contact_name: str = ""
    contact_channel: str = ""
    contact_email: str = ""
    location_province: str = ""
    export_experience_notes: str = ""
    us_export_experience: str = "unknown"
    notes: str = ""
    status: str = "new"
    supplier_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Supplier":
        return _from_dict(cls, data)


@dataclass
class ProductCandidate:
    supplier_id: str
    product_name: str
    product_url: str = ""
    product_type: str = "other"
    external_dimensions: str = ""
    internal_dimensions: str = ""
    material: str = "unknown"
    has_floor: str = "unknown"
    uv_weather_resistant: str = "unknown"
    color: str = ""
    unit_price: float | None = None
    currency: str = "USD"
    moq: int | None = None
    price_tiers: dict[str, float] = field(default_factory=dict)
    sample_cost: float | None = None
    sample_lead_time: str = ""
    production_lead_time: str = ""
    carton_size: str = ""
    gross_weight: float | None = None
    net_weight: float | None = None
    cartons_per_unit: int | None = None
    estimated_shipping_cost: float | None = None
    shipping_terms: str = ""
    packaging_notes: str = ""
    english_manual_available: str = "unknown"
    installation_video_available: str = "unknown"
    spare_parts_available: str = "unknown"
    neutral_branding_available: str = "unknown"
    warranty_or_after_sales_notes: str = ""
    assembly_notes: str = ""
    quote_date: str = ""
    raw_quote_text: str = ""
    follow_up_status: str = "not_started"
    risk_notes: list[str] = field(default_factory=list)
    product_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductCandidate":
        return _from_dict(cls, data)


@dataclass
class SupplierMessage:
    thread_id: str
    direction: str
    message_text: str
    language: str = "unknown"
    timestamp: str = field(default_factory=now_iso)
    source: str = "manual"
    extracted: bool = False
    notes: str = ""
    message_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SupplierMessage":
        return _from_dict(cls, data)


@dataclass
class SupplierThread:
    supplier_id: str
    product_ids: list[str] = field(default_factory=list)
    platform_channel: str = ""
    thread_status: str = "new"
    last_inbound_at: str = ""
    last_outbound_at: str = ""
    next_follow_up_due: str = ""
    conversation_summary: str = ""
    open_questions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    recommended_next_action: str = "prepare initial RFQ"
    messages: list[SupplierMessage] = field(default_factory=list)
    thread_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["messages"] = [message.to_dict() for message in self.messages]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SupplierThread":
        normalized = dict(data)
        normalized["messages"] = [
            item if isinstance(item, SupplierMessage) else SupplierMessage.from_dict(item)
            for item in normalized.get("messages", [])
        ]
        return _from_dict(cls, normalized)


@dataclass
class SupplierMessageDraft:
    thread_id: str
    supplier_id: str
    purpose: str
    draft_text_chinese: str
    draft_text_english: str
    approval_status: str = "pending"
    draft_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SupplierMessageDraft":
        return _from_dict(cls, data)


@dataclass
class SupplierQuoteExtraction:
    message_id: str
    product_id: str = ""
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    supplier_extracted_fields: dict[str, Any] = field(default_factory=dict)
    missing_information: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    conversation_summary: str = ""
    recommended_next_action: str = ""
    analysis_quality: str = "fallback_only"
    content_hash: str = ""


@dataclass
class SupplierFollowUpPlan:
    thread_id: str
    purpose: str = "follow_up"
    missing_information: list[str] = field(default_factory=list)
    questions_english: list[str] = field(default_factory=list)
    questions_chinese: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class SupplierConfidenceScore:
    product_id: str
    score: float
    recommendation: str
    category_scores: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _from_dict(cls, data: dict[str, Any]):
    valid_fields = cls.__dataclass_fields__.keys()
    return cls(**{key: value for key, value in data.items() if key in valid_fields})
