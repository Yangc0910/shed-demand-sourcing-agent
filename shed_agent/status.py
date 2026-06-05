from __future__ import annotations

import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from shed_agent.config import AgentConfig
from shed_agent.score_observation import score_observation
from shed_agent.storage import load_observations, save_observations


def update_listing_status(
    data_path: Path,
    config: AgentConfig,
    observation_id: str | None = None,
    status: str | None = None,
    check_urls: bool = False,
) -> list[str]:
    observations = load_observations(data_path)
    changes: list[str] = []

    for observation in observations:
        if observation_id and observation.id != observation_id:
            continue
        if status:
            old_status = observation.listing_status
            observation.listing_status = status
            observation.last_seen = date.today().isoformat()
            observation.change_notes.append(f"Status changed from {old_status} to {status} on {observation.last_seen}.")
            changes.append(f"{observation.title}: {old_status} -> {status}")
        elif check_urls and observation.url:
            if _url_available(observation.url):
                observation.last_seen = date.today().isoformat()
                if observation.listing_status == "unknown":
                    observation.listing_status = "active"
            else:
                old_status = observation.listing_status
                observation.listing_status = "disappeared"
                observation.change_notes.append(f"URL unavailable on {date.today().isoformat()}.")
                changes.append(f"{observation.title}: {old_status} -> disappeared")

    save_observations([score_observation(item, config) for item in observations], data_path)
    return changes


def _url_available(url: str) -> bool:
    if url.startswith("file://"):
        return Path(url.removeprefix("file://")).exists()
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "shed-agent-private-mvp/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, ValueError):
        return False
