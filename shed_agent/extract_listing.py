from __future__ import annotations

import re

from shed_agent.models import MarketObservation, PricePoint


BRANDS = ("suncast", "keter", "lifetime", "rubbermaid", "craftsman", "garden igloo", "palram", "arrow")
PRICE_RE = re.compile(r"(?:\$|usd\s*)(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)", re.IGNORECASE)
SIZE_RE = re.compile(
    r"(\d{1,2})\s*(?:ft\.?|feet|foot|')?(?:\s*[wd]\b)?\s*(?:x|by|×)\s*(\d{1,2})\s*(?:ft\.?|feet|foot|')?(?:\s*[wd]\b)?",
    re.IGNORECASE,
)
FAST_MOVING_TERMS = (
    "just listed",
    "listed today",
    "pending",
    "sold",
    "price drop",
    "reduced",
    "high interest",
    "popular",
    "views",
    "saves",
    "likes",
    "comments",
)


def extract_listing(
    raw_text: str,
    source: str = "manual",
    source_type: str = "manual",
    url: str = "",
    location: str = "",
) -> MarketObservation:
    text = raw_text.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else ""
    size_raw = _extract_size(text)
    brand_raw = _extract_brand(text)
    product_type = _infer_product_type(text, size_raw)
    inferred_size_category = _infer_size_category(size_raw, text, product_type)
    target_sku_fit = _infer_target_sku_fit(product_type, inferred_size_category)
    pickup_required = _pickup_required(text)
    delivery_mentioned = _delivery_mentioned(text)
    assembly_mentioned = _assembly_mentioned(text)

    observation = MarketObservation(
        source=source,
        source_type=source_type,
        title=title,
        url=url,
        price=_extract_price(text),
        location=location or _extract_location_hint(text),
        size_raw=size_raw,
        inferred_size_category=inferred_size_category,
        brand_raw=brand_raw,
        inferred_brand=brand_raw or "unknown",
        condition=_extract_condition(text),
        description_raw=text,
        product_type=product_type,
        target_sku_fit=target_sku_fit,
        delivery_mentioned=delivery_mentioned,
        assembly_mentioned=assembly_mentioned,
        pickup_required=pickup_required,
        permit_or_placement_mentions=_permit_or_placement_mentions(text),
        listing_status="active" if url else "unknown",
        extraction_notes=_extraction_notes(text, product_type, target_sku_fit, pickup_required),
    )
    if observation.price is not None:
        observation.price_history.append(PricePoint(price=observation.price, date_seen=observation.date_seen))
    return observation


def refresh_extraction(observation: MarketObservation) -> MarketObservation:
    updated = extract_listing(
        observation.description_raw,
        source=observation.source,
        source_type=observation.source_type,
        url=observation.url,
        location=observation.location,
    )
    preserved = observation.to_dict()
    refreshed = updated.to_dict()
    preserved.update(
        {
            key: refreshed[key]
            for key in (
                "price",
                "title",
                "location",
                "size_raw",
                "inferred_size_category",
                "brand_raw",
                "inferred_brand",
                "condition",
                "product_type",
                "target_sku_fit",
                "delivery_mentioned",
                "assembly_mentioned",
                "pickup_required",
                "permit_or_placement_mentions",
                "extraction_notes",
            )
        }
    )
    for key in ("search_keyword", "thumbnail_url", "image_urls", "posted_time", "source_metadata"):
        preserved.setdefault(key, observation.to_dict().get(key))
    return MarketObservation.from_dict(preserved)


def _extract_price(text: str) -> float | None:
    match = PRICE_RE.search(text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def _extract_size(text: str) -> str:
    match = SIZE_RE.search(text)
    if not match:
        return ""
    return f"{match.group(1)}x{match.group(2)}"


def _extract_brand(text: str) -> str:
    lower_text = text.lower()
    for brand in BRANDS:
        if brand in lower_text:
            return brand.title()
    return ""


def _extract_condition(text: str) -> str:
    lower_text = text.lower()
    if any(term in lower_text for term in ("new in box", "brand new", "new/unused")):
        return "new"
    if any(term in lower_text for term in ("like new", "barely used")):
        return "like new"
    if "open box" in lower_text:
        return "open box"
    if "used" in lower_text:
        return "used"
    return "unknown"


def _extract_location_hint(text: str) -> str:
    match = re.search(r"\b([A-Z][A-Za-z .'-]+,\s*(?:MA|Massachusetts))\b", text)
    if match:
        return match.group(1).strip()
    for town in ("Lexington", "Burlington", "Waltham", "Arlington", "Bedford", "Belmont", "Winchester", "Newton"):
        if town.lower() in text.lower():
            return town
    return ""


def _infer_product_type(text: str, size_raw: str) -> str:
    lower_text = text.lower()
    if any(term in lower_text for term in ("garden igloo", "garden dome", "igloo dome", "geodesic dome", "backyard dome")):
        return "garden_dome"
    if any(term in lower_text for term in ("greenhouse", "green house", "polycarbonate greenhouse")):
        return "greenhouse"
    if any(term in lower_text for term in ("canopy", "gazebo", "pergola", "pop up tent", "popup tent")):
        return "canopy_gazebo"
    if any(term in lower_text for term in ("bike shed", "bicycle storage", "bike storage")):
        return "bike_storage"
    if any(term in lower_text for term in ("shelf kit", "shed shelf", "shed shelves", "anchor kit", "base kit", "shed lock", "shed accessory")):
        return "shed_accessory"
    if any(term in lower_text for term in ("deck box", "storage box", "patio box", "outdoor storage box")):
        return "deck_box"
    if any(term in lower_text for term in ("patio storage", "cushion storage", "outdoor storage cabinet", "storage bench")):
        return "patio_storage"
    if _is_large_size(size_raw) or any(size in lower_text for size in ("7x7", "7 x 7", "8x10", "8 x 10", "10x8", "10 x 8")):
        return "large_shed"
    if any(term in lower_text for term in ("horizontal", "low profile", "low-profile")):
        return "horizontal_shed"
    if "vertical" in lower_text or "upright" in lower_text:
        return "vertical_shed"
    if "shed" in lower_text and any(term in lower_text for term in ("resin", "plastic", "polypropylene", "pp", "outdoor storage")):
        return "horizontal_shed" if size_raw in {"4x6", "6x4"} else "vertical_shed" if size_raw in {"6x5", "5x6"} else "other"
    if any(term in lower_text for term in ("backyard structure", "outdoor structure", "yard structure")):
        return "backyard_structure"
    return "other"


def _infer_size_category(size_raw: str, text: str, product_type: str) -> str:
    normalized = size_raw.lower().replace(" ", "")
    if product_type == "deck_box":
        return "deck_box"
    if product_type == "patio_storage":
        return "patio_storage"
    if product_type in {"garden_dome", "greenhouse", "canopy_gazebo", "bike_storage", "shed_accessory"}:
        return product_type
    if normalized in {"4x6", "6x4"} and product_type == "horizontal_shed":
        return "4x6_horizontal"
    if normalized in {"6x5", "5x6"} and product_type == "vertical_shed":
        return "6x5_vertical"
    if normalized:
        return normalized
    lower_text = text.lower()
    if "horizontal" in lower_text:
        return "horizontal_unknown_size"
    if "vertical" in lower_text:
        return "vertical_unknown_size"
    return "unknown"


def _infer_target_sku_fit(product_type: str, size_category: str) -> str:
    if size_category in {"4x6_horizontal", "6x5_vertical"}:
        return size_category
    if product_type in {
        "horizontal_shed",
        "vertical_shed",
        "deck_box",
        "garden_dome",
        "greenhouse",
        "canopy_gazebo",
        "patio_storage",
        "bike_storage",
        "backyard_structure",
        "shed_accessory",
    }:
        return "adjacent_expansion"
    return "not_relevant"


def _delivery_mentioned(text: str) -> bool:
    lower_text = text.lower()
    return any(
        term in lower_text
        for term in (
            "deliver",
            "delivery available",
            "can deliver",
            "will deliver",
            "local delivery",
            "drop off",
            "drop-off",
            "dropoff",
        )
    )


def _assembly_mentioned(text: str) -> bool:
    lower_text = text.lower()
    return any(
        term in lower_text
        for term in (
            "assembl",
            "installed",
            "install available",
            "setup",
            "set up",
            "disassembled",
            "disassemble",
            "take apart",
            "must be taken apart",
            "buyer disassembles",
            "needs to be assembled",
        )
    )


def _pickup_required(text: str) -> bool:
    lower_text = text.lower()
    return any(
        term in lower_text
        for term in (
            "must pick up",
            "pickup only",
            "pick up only",
            "local pickup",
            "you pick up",
            "buyer pickup",
            "buyer pick up",
            "door pickup",
            "bring truck",
            "bring a truck",
            "haul away",
            "buyer moves",
            "must haul",
            "no delivery",
        )
    )


def missing_parts_or_damage_risk(text: str) -> bool:
    lower_text = text.lower()
    return any(
        term in lower_text
        for term in (
            "missing",
            "missing parts",
            "missing hardware",
            "missing screws",
            "crack",
            "cracked",
            "broken",
            "damaged",
            "leak",
            "leaks",
            "no manual",
            "not sure all parts",
            "as is",
        )
    )


def fast_moving_signal(text: str) -> bool:
    lower_text = text.lower()
    return any(term in lower_text for term in FAST_MOVING_TERMS)


def _permit_or_placement_mentions(text: str) -> bool:
    lower_text = text.lower()
    return any(term in lower_text for term in ("permit", "hoa", "setback", "placement", "backyard", "foundation", "base kit"))


def _is_large_size(size_raw: str) -> bool:
    match = re.fullmatch(r"(\d{1,2})x(\d{1,2})", size_raw)
    if not match:
        return False
    return int(match.group(1)) * int(match.group(2)) > 36


def _extraction_notes(text: str, product_type: str, target_sku_fit: str, pickup_required: bool) -> list[str]:
    notes = [f"Classified as {product_type} with target fit {target_sku_fit}."]
    if pickup_required:
        notes.append("Pickup or hauling friction detected.")
    if "no delivery" in text.lower():
        notes.append("Listing explicitly says delivery is not offered.")
    if missing_parts_or_damage_risk(text):
        notes.append("Missing parts or damage risk detected.")
    if fast_moving_signal(text):
        notes.append("Fast-moving or visible-interest signal detected.")
    return notes
