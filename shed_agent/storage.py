from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from shed_agent.models import MarketObservation


DEFAULT_DATA_PATH = Path("data/observations.json")


def load_observations(path: Path = DEFAULT_DATA_PATH) -> list[MarketObservation]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return [MarketObservation.from_dict(item) for item in data]


def save_observations(observations: list[MarketObservation], path: Path = DEFAULT_DATA_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)
            json.dump([item.to_dict() for item in observations], file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def add_observation(observation: MarketObservation, path: Path = DEFAULT_DATA_PATH) -> MarketObservation:
    observations = load_observations(path)
    observations.append(observation)
    save_observations(observations, path)
    return observation


def replace_observations(observations: list[MarketObservation], path: Path = DEFAULT_DATA_PATH) -> None:
    save_observations(observations, path)
