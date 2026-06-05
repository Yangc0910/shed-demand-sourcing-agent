from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from shed_agent.config import AgentConfig
from shed_agent.extract_listing import extract_listing
from shed_agent.models import MarketObservation
from shed_agent.score_observation import score_observation
from shed_agent.storage import load_observations, save_observations


RETAIL_SOURCE_TYPES = {
    "amazon.com": "amazon_retail",
    "walmart.com": "walmart_retail",
    "homedepot.com": "homedepot_retail",
    "homedepot": "homedepot_retail",
    "lowes.com": "lowes_retail",
    "costco.com": "costco_retail",
}
BLOCK_TERMS = (
    "robot check",
    "captcha",
    "enter the characters you see below",
    "verify you are a human",
    "are you a robot",
    "access denied",
    "blocked",
    "automated access",
    "unusual traffic",
)


@dataclass
class RetailFetchResult:
    added: int = 0
    blocked: int = 0
    failed: int = 0
    messages: list[str] = field(default_factory=list)


def add_retail_comparable_from_text(
    raw_text: str,
    url: str = "",
    retailer: str = "",
    source_type: str = "",
    notes: str = "",
    config: AgentConfig | None = None,
) -> MarketObservation:
    config = config or AgentConfig()
    retailer = retailer or infer_retailer(url)
    source_type = source_type or infer_retail_source_type(retailer, url)
    observation = extract_listing(raw_text, source=retailer or "retail", source_type=source_type, url=url)
    metadata = extract_retail_metadata(raw_text, url, retailer)
    _apply_retail_metadata(observation, metadata, notes)
    return score_observation(observation, config)


def ingest_retail_comparable_urls(config: AgentConfig, data_path: Path, urls: list[str] | None = None) -> RetailFetchResult:
    urls = urls or config.retail_comparable_urls
    result = RetailFetchResult()
    if not urls:
        result.messages.append("No retail comparable URLs configured.")
        return result

    observations = load_observations(data_path)
    existing_urls = {item.url for item in observations if item.url}
    incoming: list[MarketObservation] = []
    for url in urls:
        if url in existing_urls:
            result.messages.append(f"Skipped existing retail URL: {url}")
            continue
        raw_text, status = safe_fetch_retail_url(url)
        retailer = infer_retailer(url)
        source_type = infer_retail_source_type(retailer, url)
        if status == "blocked":
            result.blocked += 1
            incoming.append(_blocked_observation(url, retailer, source_type, raw_text))
            result.messages.append(f"Blocked/robot-check page recorded for {url}")
            continue
        if status != "ok":
            result.failed += 1
            result.messages.append(f"Fetch failed for {url}: {status}")
            continue
        incoming.append(add_retail_comparable_from_text(raw_text, url, retailer, source_type, config=config))
        result.added += 1

    if incoming:
        observations.extend(incoming)
        save_observations(observations, data_path)
    return result


def safe_fetch_retail_url(url: str) -> tuple[str, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "ShedDemandListener/1.0 private retail benchmark; low-frequency manual URL check",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            content = response.read(300_000)
            text = content.decode("utf-8", errors="replace")
    except HTTPError as exc:
        if exc.code in {401, 403, 429, 503}:
            return f"HTTP {exc.code}", "blocked"
        return "", f"http_error_{exc.code}"
    except (OSError, URLError) as exc:
        return "", f"fetch_error: {exc}"
    if is_blocked_or_robot_check(text):
        return text[:4000], "blocked"
    return html_to_text(text)[:12000], "ok"


def is_blocked_or_robot_check(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in BLOCK_TERMS)


def extract_retail_metadata(raw_text: str, url: str = "", retailer: str = "") -> dict[str, object]:
    return {
        "retailer": retailer or infer_retailer(url),
        "product_title": _best_title(raw_text),
        "brand": _extract_brand_line(raw_text),
        "size": _extract_size(raw_text),
        "product_type": extract_listing(raw_text).product_type,
        "price": _extract_price(raw_text),
        "rating": _extract_rating(raw_text),
        "review_count": _extract_review_count(raw_text),
        "delivery_available": _delivery_available(raw_text),
        "delivery_cost_if_known": _delivery_cost(raw_text),
        "assembly_service_available": _assembly_available(raw_text),
        "return_policy_notes": _line_with(raw_text, ("return", "returns")),
        "warranty_notes": _line_with(raw_text, ("warranty",)),
        "raw_text": raw_text.strip(),
        "date_seen": date.today().isoformat(),
    }


def infer_retailer(url_or_name: str) -> str:
    value = url_or_name.strip()
    if not value:
        return "retail"
    host = urlparse(value).netloc.lower()
    normalized = host or value.lower()
    if "amazon" in normalized:
        return "Amazon"
    if "walmart" in normalized:
        return "Walmart"
    if "homedepot" in normalized or "home depot" in normalized:
        return "Home Depot"
    if "lowes" in normalized or "lowe" in normalized:
        return "Lowe's"
    if "costco" in normalized:
        return "Costco"
    return value if not host else host.replace("www.", "")


def infer_retail_source_type(retailer: str, url: str = "") -> str:
    value = f"{retailer} {url}".lower()
    if "amazon" in value:
        return "amazon_retail"
    if "walmart" in value:
        return "walmart_retail"
    if "home depot" in value or "homedepot" in value:
        return "homedepot_retail"
    if "lowe" in value or "lowes" in value:
        return "lowes_retail"
    if "costco" in value:
        return "costco_retail"
    return "retail_comparable"


def html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", "\n", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&quot;", '"', text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _apply_retail_metadata(observation: MarketObservation, metadata: dict[str, object], notes: str = "") -> None:
    observation.retailer = str(metadata.get("retailer") or observation.source)
    observation.product_title = str(metadata.get("product_title") or observation.title)
    observation.title = observation.product_title or observation.title
    observation.brand_raw = str(metadata.get("brand") or observation.brand_raw)
    observation.inferred_brand = observation.brand_raw or observation.inferred_brand
    observation.size_raw = str(metadata.get("size") or observation.size_raw)
    observation.price = metadata.get("price") if metadata.get("price") is not None else observation.price
    observation.rating = metadata.get("rating")
    observation.review_count = metadata.get("review_count")
    observation.delivery_available = bool(metadata.get("delivery_available"))
    observation.delivery_mentioned = observation.delivery_available
    observation.delivery_cost_if_known = str(metadata.get("delivery_cost_if_known") or "")
    observation.assembly_service_available = bool(metadata.get("assembly_service_available"))
    observation.assembly_mentioned = observation.assembly_service_available
    observation.return_policy_notes = str(metadata.get("return_policy_notes") or "")
    observation.warranty_notes = str(metadata.get("warranty_notes") or "")
    observation.notes = notes
    observation.source_metadata.update({"retail_metadata": metadata})


def _blocked_observation(url: str, retailer: str, source_type: str, raw_text: str) -> MarketObservation:
    observation = MarketObservation(
        source=retailer,
        source_type=source_type,
        title=f"{retailer} retail page blocked",
        url=url,
        description_raw=raw_text,
        listing_status="unknown",
        retailer=retailer,
        product_title=f"{retailer} retail page blocked",
        fetch_status="blocked",
        notes="Retail URL fetch stopped because the page appeared blocked or required robot/human verification.",
    )
    observation.extraction_notes.append("Blocked/robot-check retail page recorded without bypass attempt.")
    return observation


def _best_title(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:12]:
        if "$" not in line and not re.search(r"^(rating|reviews?|shipping|delivery|pickup)$", line, re.I):
            return line[:180]
    return lines[0][:180] if lines else ""


def _extract_price(text: str) -> float | None:
    match = re.search(r"\$(\d{2,5}(?:,\d{3})?(?:\.\d{2})?)", text)
    return float(match.group(1).replace(",", "")) if match else None


def _extract_size(text: str) -> str:
    match = re.search(r"(\d{1,2})\s*(?:ft\.?|feet|foot|')?\s*(?:x|by|×)\s*(\d{1,2})", text, re.I)
    return f"{match.group(1)}x{match.group(2)}" if match else ""


def _extract_brand_line(text: str) -> str:
    lower = text.lower()
    for brand in ("suncast", "keter", "lifetime", "rubbermaid", "craftsman", "arrow", "palram"):
        if brand in lower:
            return brand.title()
    match = re.search(r"\bBrand\s*[:\n]\s*([A-Za-z][A-Za-z0-9 '&-]{1,40})", text, re.I)
    return match.group(1).strip() if match else ""


def _extract_rating(text: str) -> float | None:
    match = re.search(r"(\d(?:\.\d)?)\s*(?:out of\s*)?5\s*stars?", text, re.I)
    return float(match.group(1)) if match else None


def _extract_review_count(text: str) -> int | None:
    match = re.search(r"([\d,]+)\s+(?:customer\s+)?reviews?", text, re.I)
    return int(match.group(1).replace(",", "")) if match else None


def _delivery_available(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in ("delivery available", "free delivery", "scheduled delivery", "ship to home", "home delivery"))


def _delivery_cost(text: str) -> str:
    line = _line_with(text, ("delivery", "shipping"))
    return line[:160]


def _assembly_available(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in ("assembly service", "professional assembly", "installation available", "add assembly"))


def _line_with(text: str, terms: tuple[str, ...]) -> str:
    for line in [line.strip() for line in text.splitlines() if line.strip()]:
        if any(term in line.lower() for term in terms):
            return line[:220]
    return ""
