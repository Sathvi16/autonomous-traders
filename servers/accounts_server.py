"""MCP adapter for account and simulated trade operations."""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from config import settings
from domain.errors import TradingError
from domain.models import TradeAction, TradeRequest
from repositories.account_repository import JsonAccountRepository
from services.account_service import AccountService


mcp = FastMCP("Accounts Server")
account_service = AccountService(
    JsonAccountRepository(settings.accounts_file)
)


def _error_response(error: Exception) -> dict[str, Any]:
    return {"success": False, "error": str(error)}


@mcp.tool()
def get_account(trader_name: str) -> dict[str, Any]:
    """Return cash and holdings for a trader."""
    try:
        return account_service.get_account(trader_name)
    except TradingError as error:
        return _error_response(error)


@mcp.tool()
def execute_trade(
    trader_name: str,
    action: str,
    stock: str,
    price: float,
    quantity: int,
) -> dict[str, Any]:
    """Validate and execute a simulated BUY, SELL, or HOLD."""
    try:
        normalized_action = TradeAction(str(action).upper().strip())
        request = TradeRequest(
            trader_name=trader_name,
            action=normalized_action,
            stock=str(stock).upper().strip(),
            price=float(price),
            quantity=int(quantity),
        )
        return account_service.execute_trade(request)
    except (TradingError, ValueError, TypeError) as error:
        return _error_response(error)


@mcp.resource("accounts://{trader_name}")
def account_resource(trader_name: str) -> str:
    """Expose account data as an MCP resource."""
    return json.dumps(get_account(trader_name), indent=4)


if __name__ == "__main__":
    mcp.run()
