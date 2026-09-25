import json
import logging
import math
from pathlib import Path

import ollama

from client.mcp_client import call_mcp_tool
from config import settings
from repositories.memory_repository import JsonMemoryRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_FILE = PROJECT_ROOT / "data" / "memory.json"

logger = logging.getLogger(__name__)
memory_repository = JsonMemoryRepository(settings.memory_file)


# ============================================================
# MEMORY
# ============================================================

def load_memory() -> dict:
    return memory_repository.load()


def save_memory(memory: dict) -> None:
    memory_repository.save(memory)


# ============================================================
# ACCOUNT HELPERS
# ============================================================

def get_cash(account: dict) -> float:
    return float(account.get("cash", 0))


def get_holdings(account: dict) -> dict:
    holdings = account.get("holdings", {})

    if not isinstance(holdings, dict):
        return {}

    return {
        str(stock).upper(): int(shares)
        for stock, shares in holdings.items()
    }


def get_owned_shares(account: dict, stock: str) -> int:
    holdings = get_holdings(account)
    return int(holdings.get(stock.upper(), 0))


# ============================================================
# TRADE LIMITS
# ============================================================

def calculate_trade_limits(
    account: dict,
    stock: str,
    current_price: float,
) -> dict:

    cash = get_cash(account)
    owned_shares = get_owned_shares(account, stock)

    if not math.isfinite(current_price) or current_price <= 0:
        return {
            "max_buy_quantity": 0,
            "max_sell_quantity": owned_shares,
        }

    max_buy_quantity = int(cash // current_price)
    if settings.max_trade_value > 0:
        max_buy_quantity = min(
            max_buy_quantity,
            int(settings.max_trade_value // current_price),
        )

    return {
        "max_buy_quantity": max_buy_quantity,
        "max_sell_quantity": owned_shares,
    }


# ============================================================
# OLLAMA RESPONSE PARSER
# ============================================================

def parse_ollama_response(response_text: str) -> dict:
    """
    Convert Ollama's response into a predictable dictionary.

    Expected format:

    {
        "action": "BUY",
        "quantity": 5,
        "reason": "..."
    }
    """

    if not response_text:
        return {
            "success": False,
            "error": "Ollama returned an empty response.",
        }

    text = response_text.strip()

    # Remove markdown code fences if the model adds them.
    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # Try direct JSON parsing.
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Sometimes the model adds explanatory text before/after JSON.
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            return {
                "success": False,
                "error": "Ollama returned invalid JSON.",
                "raw_response": response_text,
            }

        json_text = text[start:end + 1]

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Ollama returned invalid JSON.",
                "raw_response": response_text,
            }

    if not isinstance(parsed, dict):
        return {
            "success": False,
            "error": "Ollama JSON response is not an object.",
            "raw_response": response_text,
        }

    action = str(parsed.get("action", "")).upper().strip()

    if action not in {"BUY", "SELL", "HOLD"}:
        return {
            "success": False,
            "error": f"Invalid action returned by Ollama: {action}",
            "raw_response": response_text,
        }

    try:
        quantity = int(parsed.get("quantity", 0))
    except (TypeError, ValueError):
        return {
            "success": False,
            "error": "Ollama quantity must be an integer.",
            "raw_response": response_text,
        }

    if quantity < 0:
        return {
            "success": False,
            "error": "Ollama quantity cannot be negative.",
            "raw_response": response_text,
        }

    reason = str(
        parsed.get(
            "reason",
            "No reason provided by Ollama.",
        )
    )

    return {
        "success": True,
        "action": action,
        "quantity": quantity,
        "reason": reason,
        "raw_response": response_text,
    }


# ============================================================
# LLM DECISION
# ============================================================

def ask_ollama(
    trader_name: str,
    stock: str,
    current_price: float,
    account: dict,
    research: dict,
    limits: dict,
) -> dict:

    cash = get_cash(account)
    holdings = get_holdings(account)
    owned_shares = get_owned_shares(account, stock)

    trend = research.get("trend", "UNKNOWN")

    prices = research.get("prices", [])

    prompt = f"""
You are an autonomous equity trading agent.

Your job is to analyze the supplied market research and make ONE
trading decision for the stock.

TRADER
------
Trader: {trader_name}

STOCK
-----
Symbol: {stock}
Current price: ${current_price:.2f}

ACCOUNT
-------
Available cash: ${cash:.2f}
Current holdings: {json.dumps(holdings)}
Current {stock} shares: {owned_shares}

MARKET RESEARCH
---------------
Trend: {trend}
Price history: {json.dumps(prices)}

TRADE LIMITS
------------
Maximum BUY quantity: {limits["max_buy_quantity"]}
Maximum SELL quantity: {limits["max_sell_quantity"]}

DECISION RULES
--------------

1. Analyze the supplied trend and price history.

2. Follow this strategy exactly:
   - STRONG_UPWARD means SELL because the price is increasing.
   - STRONG_DOWNWARD means BUY because the price is decreasing.
   - STABLE or UNKNOWN means HOLD.

3. Do not invent market information that is not present in the research.

4. If you choose BUY, the quantity MUST NOT exceed:
   {limits["max_buy_quantity"]}

5. If you choose SELL, the quantity MUST NOT exceed:
   {limits["max_sell_quantity"]}

6. If the trader owns zero shares of {stock}, do not SELL it.
   In that situation choose BUY or HOLD.

7. If there is not enough cash to buy any share, do not BUY.

8. Return ONLY valid JSON.
    Do not use markdown.
    Do not add explanations outside the JSON.

Required JSON format:

{{
    "action": "BUY",
    "quantity": 1,
    "reason": (
        "Explain briefly why the supplied evidence supports this decision."
    )
}}
"""

    try:
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a disciplined autonomous trading decision "
                        "agent. Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            format="json",
        )

        response_text = response["message"]["content"]

        parsed = parse_ollama_response(response_text)

        if not parsed["success"]:
            return parsed

        return parsed

    except Exception as error:
        return {
            "success": False,
            "error": f"Ollama request failed: {error}",
        }


# ============================================================
# SAFETY VALIDATION
# ============================================================

def validate_trade_constraints(
    decision: dict,
    limits: dict,
    account: dict,
    stock: str,
) -> dict:

    if not decision.get("success"):
        return {
            "action": "HOLD",
            "quantity": 0,
            "validation_status": "REJECTED",
            "reason": decision.get(
                "error",
                "Invalid LLM decision.",
            ),
        }

    action = decision["action"]
    requested_quantity = int(decision.get("quantity", 0))
    llm_reason = decision.get("reason", "")

    owned_shares = get_owned_shares(account, stock)

    # --------------------------------------------------------
    # HOLD
    # --------------------------------------------------------

    if action == "HOLD":
        return {
            "action": "HOLD",
            "quantity": 0,
            "validation_status": "APPROVED",
            "reason": llm_reason,
        }

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if action == "BUY":

        max_buy = limits["max_buy_quantity"]

        if max_buy <= 0:
            return {
                "action": "HOLD",
                "quantity": 0,
                "validation_status": "REJECTED",
                "reason": (
                    f"LLM requested BUY, but there is insufficient "
                    f"cash to buy one share of {stock}."
                ),
            }

        quantity = min(requested_quantity, max_buy)

        if quantity <= 0:
            return {
                "action": "HOLD",
                "quantity": 0,
                "validation_status": "REJECTED",
                "reason": (
                    "LLM selected BUY but returned quantity 0."
                ),
            }

        return {
            "action": "BUY",
            "quantity": quantity,
            "validation_status": "APPROVED",
            "reason": llm_reason,
        }

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    if action == "SELL":

        if owned_shares <= 0:
            return {
                "action": "HOLD",
                "quantity": 0,
                "validation_status": "REJECTED",
                "reason": (
                    f"LLM requested SELL for {stock}, but the trader "
                    f"owns 0 shares."
                ),
            }

        quantity = min(
            requested_quantity,
            limits["max_sell_quantity"],
        )

        if quantity <= 0:
            return {
                "action": "HOLD",
                "quantity": 0,
                "validation_status": "REJECTED",
                "reason": (
                    "LLM selected SELL but returned quantity 0."
                ),
            }

        return {
            "action": "SELL",
            "quantity": quantity,
            "validation_status": "APPROVED",
            "reason": llm_reason,
        }

    return {
        "action": "HOLD",
        "quantity": 0,
        "validation_status": "REJECTED",
        "reason": f"Unsupported LLM action: {action}",
    }


def apply_trend_strategy(
    decision: dict,
    research: dict,
) -> dict:
    """Enforce the configured contrarian trend-to-action policy."""

    if not decision.get("success"):
        return decision

    expected_action = {
        "STRONG_UPWARD": "SELL",
        "STRONG_DOWNWARD": "BUY",
        "STABLE": "HOLD",
    }.get(research.get("trend"), "HOLD")

    updated = dict(decision)
    requested_action = updated.get("action")
    updated["action"] = expected_action

    if expected_action == "HOLD":
        updated["quantity"] = 0

    if requested_action != expected_action:
        updated["reason"] = (
            f"Trend strategy changed the proposed action from "
            f"{requested_action} to {expected_action}. "
            f"{updated.get('reason', '')}"
        ).strip()

    return updated


# ============================================================
# MAIN TRADER
# ============================================================

async def run_trader(
    trader_name: str,
    stock: str,
) -> dict:

    stock = stock.upper().strip()

    if not stock:
        raise ValueError("Stock symbol cannot be empty.")

    print(
        f"\n[{trader_name}] Starting analysis for {stock}"
    )

    # ========================================================
    # 1. GET ACCOUNT
    # ========================================================

    account = await call_mcp_tool(
        "accounts",
        "get_account",
        {
            "trader_name": trader_name,
        },
    )

    if not account.get("success"):
        raise RuntimeError(
            f"Unable to get account for {trader_name}: {account}"
        )

    # ========================================================
    # 2. GET CURRENT MARKET PRICE
    # ========================================================

    market = await call_mcp_tool(
        "market",
        "get_price",
        {
            "stock": stock,
        },
    )

    if not market.get("success"):
        raise RuntimeError(
            f"Unable to get market price for {stock}: {market}"
        )

    current_price = float(market["price"])

    # ========================================================
    # 3. GET 7-DAY MARKET HISTORY
    # ========================================================

    market_history = await call_mcp_tool(
        "market",
        "get_market_history",
        {
            "stock": stock,
            "days": settings.market_history_days,
        },
    )

    if not market_history.get("success"):
        raise RuntimeError(
            f"Unable to get market history for {stock}: "
            f"{market_history}"
        )

    prices = market_history.get("prices", [])

    if not prices:
        raise RuntimeError(
            f"No historical prices returned for {stock}."
        )

    # ========================================================
    # 4. RESEARCH
    # ========================================================

    research = await call_mcp_tool(
        "research",
        "research_stock",
        {
            "stock": stock,
            "prices": prices,
        },
    )

    if not research.get("success"):
        raise RuntimeError(
            f"Research failed for {stock}: {research}"
        )

    trend = research.get("trend", "UNKNOWN")

    # Add prices to research so the LLM can see them.
    research["prices"] = prices

    # ========================================================
    # 5. CALCULATE SAFETY LIMITS
    # ========================================================

    limits = calculate_trade_limits(
        account,
        stock,
        current_price,
    )

    # ========================================================
    # 6. ASK LLM TO MAKE THE DECISION
    # ========================================================

    llm_decision = ask_ollama(
        trader_name=trader_name,
        stock=stock,
        current_price=current_price,
        account=account,
        research=research,
        limits=limits,
    )

    strategy_decision = apply_trend_strategy(
        decision=llm_decision,
        research=research,
    )

    # ========================================================
    # 7. VALIDATE LLM DECISION
    # ========================================================

    decision = validate_trade_constraints(
        decision=strategy_decision,
        limits=limits,
        account=account,
        stock=stock,
    )

    # ========================================================
    # 8. EXECUTE TRADE
    # ========================================================

    trade_result = None

    if (
        decision["validation_status"] == "APPROVED"
        and decision["action"] in {"BUY", "SELL"}
        and decision["quantity"] > 0
    ):

        trade_result = await call_mcp_tool(
            "accounts",
            "execute_trade",
            {
                "trader_name": trader_name,
                "action": decision["action"],
                "stock": stock,
                "price": current_price,
                "quantity": decision["quantity"],
            },
        )
        if not trade_result.get("success"):
            logger.error(
                "Trade execution failed for %s/%s: %s",
                trader_name,
                stock,
                trade_result,
            )

    # ========================================================
    # 9. SAVE MEMORY
    # ========================================================

    memory_entry = {
            "stock": stock,
            "price": current_price,
            "trend": trend,
            "llm_action": llm_decision.get(
                "action",
                "UNKNOWN",
            ),
            "llm_quantity": llm_decision.get(
                "quantity",
                0,
            ),
            "decision": decision["action"],
            "quantity": decision["quantity"],
            "validation_status": decision[
                "validation_status"
            ],
            "reason": decision["reason"],
        }
    memory_repository.append(trader_name, memory_entry)

    # ========================================================
    # 10. RETURN RESULT
    # ========================================================

    return {
        "trader": trader_name,
        "stock": stock,
        "account": account,
        "current_price": current_price,
        "market_history": market_history,
        "research": research,
        "limits": limits,
        "llm_decision": llm_decision,
        "decision": decision,
        "trade_result": trade_result,
    }