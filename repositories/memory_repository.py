"""Decision-history persistence."""

import json
from pathlib import Path
from typing import Any


class JsonMemoryRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as file:
                value = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                f"Unable to load decision history from {self.path}: {error}"
            ) from error
        if not isinstance(value, dict):
            raise ValueError("Decision history must contain an object.")
        return value

    def append(self, trader_name: str, entry: dict[str, Any]) -> None:
        memory = self.load()
        memory.setdefault(trader_name, []).append(entry)
        self.save(memory)

    def save(self, memory: dict[str, list[dict[str, Any]]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(memory, file, indent=4)
                file.write("\n")
            temporary.replace(self.path)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
