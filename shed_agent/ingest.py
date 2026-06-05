from __future__ import annotations

import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

from shed_agent.config import AgentConfig
from shed_agent.deduplicate import merge_observations
from shed_agent.extract_listing import extract_listing
from shed_agent.models import MarketObservation
from shed_agent.score_observation import score_observation
from shed_agent.storage import load_observations, save_observations


def ingest_craigslist_rss(config: AgentConfig, data_path: Path, rss_urls: list[str] | None = None) -> tuple[int, list[str]]:
    urls = rss_urls if rss_urls is not None else config.craigslist_rss_urls
    incoming: list[MarketObservation] = []
    changes: list[str] = []
    for url in urls:
        xml_text = _fetch_text(url)
        parsed = parse_craigslist_rss(xml_text, source_url=url)
        incoming.extend(score_observation(item, config) for item in parsed)

    existing = load_observations(data_path)
    merged, new_items, merge_changes = merge_observations(existing, incoming)
    save_observations([score_observation(item, config) for item in merged], data_path)
    changes.extend(merge_changes)
    return len(new_items), changes


def ingest_watchlist(config: AgentConfig, data_path: Path, urls: list[str] | None = None) -> tuple[int, list[str]]:
    watchlist_urls = urls if urls is not None else config.watchlist_urls
    incoming = []
    changes = []
    for url in watchlist_urls:
        try:
            text = _fetch_text(url)
            observation = extract_listing(text, source=url, source_type="watchlist_url", url=url)
            changes.append(f"Fetched watchlist URL: {url}")
        except urllib.error.URLError:
            observation = extract_listing(url, source=url, source_type="watchlist_url", url=url)
            observation.notes = "Registered watchlist URL; fetch failed or was unavailable."
            changes.append(f"Registered watchlist URL without fetch: {url}")
        incoming.append(score_observation(observation, config))

    existing = load_observations(data_path)
    merged, new_items, merge_changes = merge_observations(existing, incoming)
    save_observations([score_observation(item, config) for item in merged], data_path)
    changes.extend(merge_changes)
    return len(new_items), changes


def parse_craigslist_rss(xml_text: str, source_url: str = "") -> list[MarketObservation]:
    root = ET.fromstring(xml_text)
    observations = []
    for item in root.findall(".//item"):
        title = _node_text(item, "title")
        link = _node_text(item, "link")
        description = unescape(_node_text(item, "description"))
        raw_text = "\n".join(part for part in (title, description) if part)
        observation = extract_listing(raw_text, source=source_url or "craigslist_rss", source_type="craigslist_rss", url=link)
        observation.listing_status = "active"
        observations.append(observation)
    return observations


def _fetch_text(url: str) -> str:
    if url.startswith("file://"):
        return Path(url.removeprefix("file://")).read_text(encoding="utf-8")
    request = urllib.request.Request(url, headers={"User-Agent": "shed-agent-private-mvp/0.1"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="replace")


def _node_text(item: ET.Element, name: str) -> str:
    node = item.find(name)
    return node.text.strip() if node is not None and node.text else ""
