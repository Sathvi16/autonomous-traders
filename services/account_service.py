"""Account and simulated trade business rules."""

import math
from typing import Any

from domain.errors import (
    InsufficientCashError,
    InsufficientSharesError,
    InvalidTradeError,
)
from domain.models import TradeAction, TradeRequest
from repositories.account_repository import JsonAccountRepository


class AccountService:
    def __init__(self, repository: JsonAccountRepository) -> None:
        self.repository = repository

    def get_account(self, trader_name: str) -> dict[str, Any]:
        account = self.repository.get(trader_name)
        return {
            "success": True,
            "trader": trader_name,
            **account.to_dict(),
        }

    def execute_trade(self, request: TradeRequest) -> dict[str, Any]:
        self._validate_request(request)
        accounts = self.repository.load_all()
        if request.trader_name not in accounts:
            return {
                "success": False,
                "error": f"Trader '{request.trader_name}' was not found.",
            }

        account = accounts[request.trader_name]
        current_shares = account.holdings.get(request.stock, 0)
        total_value = request.price * request.quantity

        if request.action is TradeAction.BUY:
            if total_value > account.cash:
                raise InsufficientCashError(
                    f"Insufficient cash. Required: ${total_value:.2f}, "
                    f"Available: ${account.cash:.2f}"
                )
            account.cash = round(account.cash - total_value, 2)
            account.holdings[request.stock] = (
                current_shares + request.quantity
            )
        elif request.action is TradeAction.SELL:
            if request.quantity > current_shares:
                raise InsufficientSharesError(
                    f"Insufficient shares for {request.stock}. "
                    f"Requested: {request.quantity}, Available: {current_shares}"
                )
            account.cash = round(account.cash + total_value, 2)
            remaining = current_shares - request.quantity
            if remaining:
                account.holdings[request.stock] = remaining
            else:
                account.holdings.pop(request.stock, None)

        self.repository.save_all(accounts)
        return {
            "success": True,
            "trader": request.trader_name,
            "stock": request.stock,
            "action": request.action.value,
            "quantity": request.quantity if request.action is not TradeAction.HOLD else 0,
            "price": round(request.price, 2),
            "total_value": round(total_value, 2),
            "cash": round(account.cash, 2),
            "shares": account.holdings.get(request.stock, 0),
            "holdings": account.holdings,
            "message": (
                "No trade executed."
                if request.action is TradeAction.HOLD
                else f"{request.action.value} executed successfully."
            ),
        }

    @staticmethod
    def _validate_request(request: TradeRequest) -> None:
        if not request.stock:
            raise InvalidTradeError("Stock symbol cannot be empty.")
        if not math.isfinite(request.price) or request.price <= 0:
            raise InvalidTradeError(
                "Price must be a finite number greater than zero."
            )
        if request.quantity < 0:
            raise InvalidTradeError("Quantity cannot be negative.")
        if request.action is not TradeAction.HOLD and request.quantity == 0:
            raise InvalidTradeError(
                f"{request.action.value} quantity must be greater than zero."
            )
