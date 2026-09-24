"""Typed trading domain models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Account:
    cash: float
    holdings: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"cash": self.cash, "holdings": dict(self.holdings)}


@dataclass(frozen=True)
class TradeRequest:
    trader_name: str
    action: TradeAction
    stock: str
    price: float
    quantity: int
