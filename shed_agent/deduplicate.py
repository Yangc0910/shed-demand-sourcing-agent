from __future__ import annotations

import hashlib
import re
from datetime import date

from shed_agent.models import MarketObservation, PricePoint


def observation_key(observation: MarketObservation) -> str:
    if observation.url:
        return f"url:{_normalize_url(observation.url)}"
    basis = "|".join(
        [
            _normalize_text(observation.title),
            _normalize_text(observation.location),
            observation.inferred_size_category,
            str(int(observation.price)) if observation.price is not None else "",
        ]
    )
    return f"text:{hashlib.sha1(basis.encode('utf-8')).hexdigest()}"


def merge_observations(
    existing: list[MarketObservation],
    incoming: list[MarketObservation],
) -> tuple[list[MarketObservation], list[MarketObservation], list[str]]:
    by_key = {observation_key(item): item for item in existing}
    new_items: list[MarketObservation] = []
    changes: list[str] = []

    for item in incoming:
        key = observation_key(item)
        if key not in by_key:
            by_key[key] = item
            new_items.append(item)
            changes.append(f"New listing: {item.title}")
            continue

        current = by_key[key]
        current.last_seen = date.today().isoformat()
        if current.listing_status == "disappeared":
            current.listing_status = "active"
            current.change_notes.append(f"Reappeared on {current.last_seen}.")
            changes.append(f"Reappeared listing: {current.title}")

        if item.price is not None and item.price != current.price:
            old_price = current.price
            current.price = item.price
            current.price_history.append(PricePoint(price=item.price, date_seen=current.last_seen))
            current.change_notes.append(f"Price changed from {old_price} to {item.price} on {current.last_seen}.")
            changes.append(f"Price change: {current.title} from {old_price} to {item.price}")

        if _should_update_title(current.title, item.title):
            old_title = current.title
            current.title = item.title
            current.change_notes.append(f"Listing title refined from '{old_title}' on {current.last_seen}.")
            changes.append(f"Title refined: {old_title} -> {item.title}")

        if _should_update_description(current.description_raw, item.description_raw):
            current.description_raw = item.description_raw
            current.location = item.location or current.location
            current.search_keyword = item.search_keyword or current.search_keyword
            current.thumbnail_url = item.thumbnail_url or current.thumbnail_url
            current.image_urls = item.image_urls or current.image_urls
            current.source_metadata.update(item.source_metadata)
            current.llm_content_hash = ""
            current.change_notes.append(f"Listing text updated on {current.last_seen}.")
            changes.append(f"Listing text updated: {current.title}")

    return list(by_key.values()), new_items, changes


def deduplicate_observations(observations: list[MarketObservation]) -> list[MarketObservation]:
    merged, _, _ = merge_observations([], observations)
    return merged


def _normalize_url(url: str) -> str:
    return url.strip().lower().split("?")[0].rstrip("/")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _should_update_title(current_title: str, incoming_title: str) -> bool:
    if not incoming_title or incoming_title == current_title:
        return False
    noise_titles = {"just listed", "listed today", "new listing", "sponsored"}
    return current_title.strip().lower() in noise_titles and incoming_title.strip().lower() not in noise_titles


def _should_update_description(current_text: str, incoming_text: str) -> bool:
    if not incoming_text or incoming_text == current_text:
        return False
    return len(incoming_text.strip()) > len(current_text.strip())
