"""Application configuration."""

from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass(frozen=True)
class Settings:
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    market_history_days: int = int(os.getenv("MARKET_HISTORY_DAYS", "7"))
    trend_threshold_percent: float = float(
        os.getenv("TREND_THRESHOLD_PERCENT", "2")
    )
    max_trade_value: float = float(os.getenv("MAX_TRADE_VALUE", "0"))
    data_dir: Path = DATA_DIR

    @property
    def accounts_file(self) -> Path:
        return self.data_dir / "accounts.json"

    @property
    def memory_file(self) -> Path:
        return self.data_dir / "memory.json"


settings = Settings()
