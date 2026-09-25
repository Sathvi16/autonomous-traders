import asyncio
from difflib import get_close_matches
import json
import re
import sys
from pathlib import Path
from typing import Any

from client.mcp_client import call_mcp_tool
from config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CANDIDATE_SYMBOLS = [
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AMD",
    "INTC",
    "NFLX",
    "SHOP",
    "COST",
    "MCD",
    "XOM",
    "WMT",
    "JPM",
    "V",
    "PFE",
    "UNH",
    "CRM",
    "ABNB",
    "AVGO",
    "ORCL",
    "PYPL",
    "NKE",
    "DIS",
]

STOCK_NAME_MAP = {
    "AAPL": "Apple(AAPL)",
    "AMZN": "Amazon(AMZN)",
    "AMD": "Advanced Micro Devices(AMD)",
    "ABNB": "Airbnb(ABNB)",
    "AVGO": "Broadcom(AVGO)",
    "COST": "Costco(COST)",
    "CRM": "Salesforce(CRM)",
    "DIS": "Disney(DIS)",
    "GOOGL": "Alphabet(GOOGL)",
    "INTC": "Intel(INTC)",
    "JPM": "JPMorgan Chase(JPM)",
    "MCD": "McDonald's(MCD)",
    "META": "Meta(META)",
    "MSFT": "Microsoft(MSFT)",
    "NFLX": "Netflix(NFLX)",
    "NKE": "Nike(NKE)",
    "NVDA": "NVIDIA(NVDA)",
    "ORCL": "Oracle(ORCL)",
    "PFE": "Pfizer(PFE)",
    "PYPL": "PayPal(PYPL)",
    "SHOP": "Shopify(SHOP)",
    "TSLA": "Tesla(TSLA)",
    "UNH": "UnitedHealth(UNH)",
    "V": "Visa(V)",
    "WMT": "Walmart(WMT)",
    "XOM": "Exxon Mobil(XOM)",
}

LONG_TERM_STOCKS = {
    "AAPL": ("Technology", "Established consumer technology ecosystem"),
    "MSFT": ("Technology", "Diversified software and cloud exposure"),
    "GOOGL": ("Technology", "Digital advertising and cloud exposure"),
    "AMZN": ("Consumer/Technology", "E-commerce and cloud exposure"),
    "JPM": ("Financials", "Large diversified banking franchise"),
    "V": ("Financials", "Global payments network"),
    "UNH": ("Healthcare", "Large healthcare-services business"),
    "JNJ": ("Healthcare", "Diversified healthcare business"),
    "XOM": ("Energy", "Large integrated energy exposure"),
    "COST": ("Consumer", "Membership-based retail business"),
}

INDIA_RESEARCH_LIST = [
    ("HDFC Bank", "HDFCBANK.NS", "Banking", "Large private-bank franchise"),
    ("ICICI Bank", "ICICIBANK.NS", "Banking", "Diversified private-bank exposure"),
    ("Reliance Industries", "RELIANCE.NS", "Diversified", "Energy, telecom, and retail"),
    ("Tata Consultancy Services", "TCS.NS", "IT Services", "Global technology-services business"),
    ("Bharti Airtel", "BHARTIARTL.NS", "Telecom", "Telecom and data-growth exposure"),
    ("Sun Pharma", "SUNPHARMA.NS", "Healthcare", "Large pharmaceutical business"),
    ("Larsen & Toubro", "LT.NS", "Infrastructure", "Infrastructure and capital-expenditure exposure"),
    ("ITC", "ITC.NS", "Consumer", "Diversified consumer and FMCG business"),
]

EXIT_COMMANDS = {"exit", "quit", "q"}
COMMON_WORDS = {
    "I", "AM", "THE", "AND", "OR", "TO", "BUY", "SELL", "BEST", "STOCK",
    "STOCKS", "RISK", "LOW", "MEDIUM", "HIGH", "USD", "INR", "RS", "LTD",
}


def is_exit_command(user_input: str) -> bool:
    """Recognize exit commands, including a close single-word typo."""
    normalized = user_input.strip().lower()
    if normalized in EXIT_COMMANDS:
        return True

    if " " not in normalized and "\t" not in normalized:
        return bool(
            get_close_matches(
                normalized, EXIT_COMMANDS - {"q"}, n=1, cutoff=0.6
            )
        )

    return False


def load_available_traders() -> list[str]:
    """Return trader names from the local account store."""
    try:
        accounts_path = (
            Path(__file__).resolve().parents[1] / "data" / "accounts.json"
        )
        with open(accounts_path, "r", encoding="utf-8") as file:
            accounts = __import__("json").load(file)
        return [str(name) for name in accounts.keys()]
    except Exception:
        return []


def load_conversation_memory() -> dict[str, Any]:
    """Load persisted trader context without failing the interactive agent."""
    try:
        if not settings.memory_file.exists():
            return {"current_trader": None, "traders": {}}
        with settings.memory_file.open("r", encoding="utf-8") as file:
            memory = json.load(file)
        if not isinstance(memory, dict):
            return {"current_trader": None, "traders": {}}
        memory.setdefault("current_trader", None)
        memory.setdefault("traders", {})
        return memory
    except (OSError, json.JSONDecodeError):
        return {"current_trader": None, "traders": {}}


def save_conversation_memory(memory: dict[str, Any]) -> None:
    """Persist trader context for the next prompt or process run."""
    settings.memory_file.parent.mkdir(parents=True, exist_ok=True)
    with settings.memory_file.open("w", encoding="utf-8") as file:
        json.dump(memory, file, indent=2)


def extract_investor_preferences(user_input: str) -> dict[str, Any]:
    """Extract the explicit long-term preferences from a natural-language reply."""
    preferences: dict[str, Any] = {}
    contribution_match = re.search(
        r"(?:monthly contribution|contribute|invest)\D{0,20}"
        r"([$₹]?\s?\d+(?:[,.]\d+)*)",
        user_input,
        flags=re.IGNORECASE,
    )
    if contribution_match:
        amount = contribution_match.group(1).replace(",", "")
        preferences["monthly_contribution"] = float(
            re.sub(r"[^\d.]", "", amount)
        )

    years_match = re.search(
        r"(\d+)\s*(?:\+)?\s*(?:year|years|yr|yrs)\b",
        user_input,
        flags=re.IGNORECASE,
    )
    if years_match:
        preferences["time_horizon_years"] = int(years_match.group(1))

    risk_match = re.search(
        r"\b(low|medium|moderate|high)\s*(?:risk)?\b",
        user_input,
        flags=re.IGNORECASE,
    )
    if risk_match:
        risk = risk_match.group(1).lower()
        preferences["risk_level"] = "medium" if risk == "moderate" else risk

    return preferences


def extract_investment_request(user_input: str) -> dict[str, Any]:
    """Extract budget, candidate tickers, and risk warnings from a prompt."""
    result: dict[str, Any] = {}
    capital_match = re.search(
        r"(?:capital|budget|available|invest(?:ment)? amount|lump sum)"
        r"\D{0,15}(₹|rs\.?|inr|\$)?\s*([\d,]+(?:\.\d+)?)"
        r"\s*(lakh|lac|crore)?",
        user_input,
        flags=re.IGNORECASE,
    )
    if not capital_match:
        capital_match = re.search(
            r"(₹|rs\.?|inr|\$)\s*([\d,]+(?:\.\d+)?)\s*"
            r"(lakh|lac|crore)?\s*(?:capital|budget)?",
            user_input,
            flags=re.IGNORECASE,
        )
    if not capital_match:
        capital_match = re.search(
            r"([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore)?\s*"
            r"(?:capital|budget)\b",
            user_input,
            flags=re.IGNORECASE,
        )
    if capital_match:
        first_group = capital_match.group(1)
        has_currency = first_group.lower() in {
            "₹", "rs", "rs.", "inr", "$"
        }
        amount_group = (
            capital_match.group(2) if has_currency else first_group
        )
        amount = float(amount_group.replace(",", ""))
        suffix = (
            capital_match.group(3)
            if has_currency and capital_match.lastindex >= 3
            else capital_match.group(2) if capital_match.lastindex >= 2 else None
        )
        if suffix:
            multiplier = (
                100000
                if suffix.lower() in {"lakh", "lac"}
                else 10000000
            )
            amount *= multiplier
        result["capital"] = amount
        currency = first_group if has_currency else None
        result["currency"] = (
            "INR" if currency and currency.lower() in {"₹", "rs", "rs.", "inr"}
            else "USD"
        )

    tokens = re.findall(r"\b[A-Z]{1,5}\b", user_input)
    candidates = [token for token in tokens if token not in COMMON_WORDS]
    result["candidate_symbols"] = list(dict.fromkeys(candidates))
    result["duplicate_symbols"] = sorted(
        {symbol for symbol in candidates if candidates.count(symbol) > 1}
    )
    result["invalid_symbols"] = sorted(
        set(candidates) - set(DEFAULT_CANDIDATE_SYMBOLS) - set(STOCK_NAME_MAP)
    )
    result["concentration_warning"] = bool(
        re.search(r"100\s*%|\ball\s+(?:my|the)\s+(?:money|capital|cash)",
                  user_input, flags=re.IGNORECASE)
    )
    result["asks_for_best_stock"] = bool(
        re.search(r"\b(best|top)\s+(?:stock|share|investment)\b",
                  user_input, flags=re.IGNORECASE)
    )
    return result


def normalize_trader_name(user_input: str) -> str | None:
    """Accept natural-language prompts like 'I am trader 1' or 'Trader 1'."""
    if not user_input:
        return None

    text = user_input.strip()
    if not text:
        return None

    lowered = text.lower()
    if is_exit_command(text):
        return None

    patterns = [
        (
            r"(?:i\s+am|i'm|im|my\s+name\s+is|this\s+is)?\s*"
            r"trader\s*(?:number|#)?\s*(\d+)\b"
        ),
        r"\btrader\s*(?:number|#)?\s*(\d+)\b",
        r"\bTrader\s*\d+\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            trader_number = (
                match.group(1)
                if match.lastindex
                else match.group(0).split()[-1]
            )
            return f"Trader {trader_number}"

    available = load_available_traders()
    if not available:
        return None

    question_keywords = [
        "which stock", "which stocks", "buy", "sell", "hold",
        "what should", "recommend", "portfolio", "holdings"
    ]
    if any(keyword in lowered for keyword in question_keywords):
        for candidate in available:
            candidate_lower = candidate.lower()
            if candidate_lower in lowered:
                return candidate

    return None


def classify_trend_action(trend: str) -> str:
    """Return the best action for a given trend."""
    return {
        "STRONG_UPWARD": "SELL",
        "STRONG_DOWNWARD": "BUY",
        "STABLE": "HOLD",
    }.get(trend, "HOLD")


def is_long_term_request(user_input: str) -> bool:
    """Detect requests for a multi-year investing plan."""
    normalized = user_input.lower()
    terms = (
        "long term",
        "long-term",
        "longtime",
        "long time",
        "5 year",
        "10 year",
        "years",
        "beginner",
        "maintain",
        "investing portfolio",
    )
    return any(term in normalized for term in terms)


def is_india_plan_request(user_input: str) -> bool:
    """Detect an explicit request to switch to an India-focused plan."""
    normalized = re.sub(r"[^a-z0-9]+", " ", user_input.lower()).strip()
    return bool(
        re.search(r"\bindia(?:n)?\b.*\b(?:plan|stocks?|portfolio|invest)", normalized)
        or re.search(r"\b(?:plan|stocks?|portfolio|invest).*\bindia(?:n)?\b", normalized)
    )


def format_india_plan_answer(trader: str) -> str:
    """Explain the India-plan boundary without inventing market data."""
    lines = [
        f"Of course, {trader}. I can switch this conversation to an "
        "India-focused long-term research plan.",
        (
            "Your current account data is stored as US-listed holdings and "
            "US-dollar cash, so I will not mix those values with Indian "
            "rupee allocations or pretend they are directly comparable."
        ),
        (
            "Indian companies to research across different sectors "
            "(these are watchlist candidates, not guaranteed recommendations):"
        ),
    ]
    for name, ticker, sector, reason in INDIA_RESEARCH_LIST:
        lines.append(f"- {name} ({ticker}) — {sector}: {reason}.")
    lines.extend(
        [
            (
                "For a low-risk 10-year approach, consider making a "
                "diversified Nifty 50 index fund or ETF the core and using "
                "individual stocks as a smaller satellite allocation."
            ),
            (
                "To build an India allocation without guessing, tell me the "
                "amount in INR, monthly contribution, time horizon, and "
                "low/medium/high risk preference. I will then apply the same "
                "criteria—business quality, financial strength, valuation, "
                "sector diversification, and long-term risks."
            ),
        ]
    )
    return "\n".join(lines)


async def analyze_trader_recommendations(
    trader_name: str,
    requested_symbols: list[str] | None = None,
) -> dict[str, Any]:
    account = await call_mcp_tool(
        "accounts",
        "get_account",
        {"trader_name": trader_name},
    )

    if not account.get("success"):
        return {
            "success": False,
            "trader": trader_name,
            "error": account.get("error", "Unable to fetch account."),
        }

    holdings = account.get("holdings", {})
    candidate_symbols = sorted({
        *holdings.keys(),
        *DEFAULT_CANDIDATE_SYMBOLS,
        *(requested_symbols or []),
    })
    recommendations: list[dict[str, Any]] = []

    for symbol in candidate_symbols:
        market = await call_mcp_tool(
            "market",
            "get_price",
            {"stock": symbol},
        )

        if not market.get("success"):
            continue

        history = await call_mcp_tool(
            "market",
            "get_market_history",
            {"stock": symbol, "days": settings.market_history_days},
        )

        if not history.get("success"):
            continue

        research = await call_mcp_tool(
            "research",
            "research_stock",
            {"stock": symbol, "prices": history.get("prices", [])},
        )

        if not research.get("success"):
            continue

        current_price = float(market["price"])
        owned_shares = int(holdings.get(symbol, 0))
        action = classify_trend_action(research.get("trend", "STABLE"))
        max_buy_quantity = (
            int(account["cash"] // current_price) if action == "BUY" else 0
        )

        recommendations.append(
            {
                "stock": symbol,
                "current_price": round(current_price, 2),
                "trend": research.get("trend", "STABLE"),
                "holding": owned_shares,
                "action": action,
                "max_buy_quantity": max_buy_quantity,
                "max_sell_quantity": owned_shares if action == "SELL" else 0,
                    "reason": (
                        f"Trend is {research.get('trend', 'STABLE')} and the "
                        "current "
                        f"portfolio position for {symbol} is "
                        f"{owned_shares} shares"
                ),
            }
        )

    action_priority = {"BUY": 0, "SELL": 1, "HOLD": 2}
    ordered_recommendations: list[dict[str, Any]] = []
    for item in recommendations:
        rank = (
            action_priority.get(item["action"], 99),
            item["stock"],
        )
        inserted = False
        for index, existing in enumerate(ordered_recommendations):
            existing_rank = (
                action_priority.get(existing["action"], 99),
                existing["stock"],
            )
            if rank < existing_rank:
                ordered_recommendations.insert(index, item)
                inserted = True
                break
        if not inserted:
            ordered_recommendations.append(item)
    recommendations = ordered_recommendations

    buy_recommendations = [
        item for item in recommendations if item["action"] == "BUY"
    ]
    sell_recommendations = [
        item for item in recommendations if item["action"] == "SELL"
    ]
    hold_recommendations = [
        item for item in recommendations if item["action"] == "HOLD"
    ]

    evaluated_symbols = [item["stock"] for item in recommendations]
    other_reviewed_symbols = [
        symbol for symbol in evaluated_symbols if symbol not in holdings
    ]

    return {
        "success": True,
        "trader": trader_name,
        "cash": account.get("cash", 0),
        "holdings": holdings,
        "buy_recommendations": buy_recommendations,
        "sell_recommendations": sell_recommendations,
        "hold_recommendations": hold_recommendations,
        "all_recommendations": recommendations,
        "evaluated_symbols": evaluated_symbols,
        "other_reviewed_symbols": other_reviewed_symbols,
    }


def format_symbol(symbol: str) -> str:
    return STOCK_NAME_MAP.get(symbol.upper(), symbol.upper())


def format_long_term_answer(
    analysis: dict[str, Any],
    preferences: dict[str, Any] | None = None,
    request: dict[str, Any] | None = None,
) -> str:
    """Explain a cautious, multi-year portfolio approach using available data."""
    preferences = preferences or {}
    request = request or {}
    trader = analysis["trader"]
    cash = float(analysis.get("cash", 0))
    holdings = analysis.get("holdings", {})
    recommendations = {
        item["stock"]: item
        for item in analysis.get("all_recommendations", [])
    }
    formatted_holdings = ", ".join(
        f"{format_symbol(symbol)} ({shares} shares)"
        for symbol, shares in holdings.items()
    ) or "empty"
    sections: list[str] = [
        (
            f"Thanks for sharing your goal, {trader}. If you plan to hold for "
            "5–10 years or longer, I would treat this as long-term investing "
            "rather than short-term trading."
        ),
        (
            "Your account currently has "
            f"${cash:,.2f} available and your holdings are "
            f"{formatted_holdings}."
        ),
        (
            "The short-term trend signals below are only a screening tool. "
            "They do not prove that a company is suitable for a long-term "
            "portfolio. Business quality, valuation, diversification, taxes, "
            "and your risk tolerance should be checked before investing."
        ),
    ]

    monthly_contribution = preferences.get("monthly_contribution")
    time_horizon_years = preferences.get("time_horizon_years")
    risk_level = preferences.get("risk_level")
    if monthly_contribution or time_horizon_years or risk_level:
        profile_parts = []
        if monthly_contribution:
            profile_parts.append(f"${monthly_contribution:,.2f} per month")
        if time_horizon_years:
            profile_parts.append(f"{time_horizon_years} years")
        if risk_level:
            profile_parts.append(f"{risk_level} risk")
        sections.append(
            "I’ve noted your investor profile: "
            + ", ".join(profile_parts)
            + ". I’ll use these details in future follow-up answers."
        )

    if monthly_contribution and time_horizon_years:
        total_contributions = (
            monthly_contribution * 12 * time_horizon_years
        )
        sections.append(
            f"At ${monthly_contribution:,.2f} per month for "
            f"{time_horizon_years} years, your contributions would total "
            f"about ${total_contributions:,.2f}, before any returns or fees. "
            "Returns are not guaranteed."
        )
    if risk_level == "low":
        sections.append(
            "Because you selected low risk, consider making a diversified "
            "index fund or ETF the core of the plan and keeping individual "
            "stocks as a smaller portion. Even strong companies can fall."
        )

    capital = request.get("capital")
    if capital is not None:
        currency = request.get("currency", "USD")
        sections.append(
            f"I will keep the plan within your {currency} {capital:,.2f} "
            "capital limit. The amounts below are illustrative and do not "
            "assume leverage."
        )
        if capital <= 5000:
            sections.append(
                "With a small starting amount, a practical approach is one "
                "broad index fund/ETF or two carefully selected holdings, "
                "rather than spreading the money across many tiny positions."
            )

    if request.get("concentration_warning"):
        sections.append(
            "Putting 100% of your capital into one stock creates "
            "concentration risk. A company-specific event could materially "
            "damage the portfolio, so I would not treat a single-stock "
            "allocation as a low-risk plan."
        )

    invalid_symbols = request.get("invalid_symbols", [])
    if invalid_symbols:
        sections.append(
            "I could not validate these ticker(s) in the local market "
            f"universe, so I will not invent company details for them: "
            f"{', '.join(invalid_symbols)}."
        )

    duplicate_symbols = request.get("duplicate_symbols", [])
    if duplicate_symbols:
        sections.append(
            "I detected duplicate exposure in the candidate list: "
            f"{', '.join(format_symbol(symbol) for symbol in duplicate_symbols)}. "
            "Duplicates should be counted once when assessing diversification."
        )

    if request.get("asks_for_best_stock") and not (
        time_horizon_years or risk_level
    ):
        sections.append(
            "Before naming a single best stock, I need your time horizon and "
            "risk tolerance. There is no universally best stock, and the "
            "answer changes substantially between a short-term, low-risk, "
            "and 10-year growth objective."
        )

    research_list = [
        ("AAPL", "Technology", "Established technology ecosystem"),
        ("MSFT", "Technology", "Software and cloud exposure"),
        ("GOOGL", "Technology", "Advertising and cloud exposure"),
        ("AMZN", "Consumer/Technology", "E-commerce and cloud exposure"),
        ("JPM", "Financials", "Diversified banking exposure"),
        ("V", "Financials", "Global payments exposure"),
        ("UNH", "Healthcare", "Healthcare-services exposure"),
        ("COST", "Consumer", "Membership retail exposure"),
    ]
    available_research = [
        item for item in research_list if item[0] in recommendations
    ]
    requested_symbols = request.get("candidate_symbols", [])
    if len(requested_symbols) >= 2:
        sections.append(
            "I will apply the same selection criteria to every valid "
            "candidate: business quality, financial strength, valuation, "
            "sector diversification, and long-term downside risk. "
            "A short-term trend alone will not decide a 10-year allocation."
        )
    if available_research:
        lines = ["Stocks to research for a diversified long-term watchlist:"]
        for symbol, sector, reason in available_research:
            item = recommendations[symbol]
            lines.append(
                f"- {format_symbol(symbol)} ({sector}): {reason}; "
                f"latest observed price ${item['current_price']:.2f}."
            )
        sections.append("\n".join(lines))

    allocation = [
        ("AAPL", 15),
        ("MSFT", 15),
        ("GOOGL", 10),
        ("AMZN", 10),
        ("JPM", 10),
        ("V", 10),
        ("UNH", 10),
        ("COST", 10),
    ]
    available_allocation = [
        (symbol, percentage)
        for symbol, percentage in allocation
        if symbol in recommendations
    ]
    plan_capital = capital if capital is not None else cash
    if available_allocation:
        total_percentage = sum(percentage for _, percentage in available_allocation)
        lines = [
            "Illustrative allocation for the available cash "
            "(not a guaranteed-return recommendation):"
        ]
        for symbol, percentage in available_allocation:
            amount = plan_capital * percentage / 100
            price = recommendations[symbol]["current_price"]
            shares = int(amount // price) if price > 0 else 0
            lines.append(
                f"- {format_symbol(symbol)}: {percentage}% "
                f"(about ${amount:,.2f}, up to {shares} whole shares at "
                f"${price:.2f})"
            )
        if total_percentage < 100:
            lines.append(
                f"- Keep the remaining {100 - total_percentage}% in cash or "
                "consider a diversified index fund/ETF."
            )
        sections.append("\n".join(lines))

    sections.append(
        "For long-term selection, I compare business quality, financial "
        "strength, valuation, competitive advantages, sector concentration, "
        "and risks such as debt, regulation, disruption, and permanent "
        "loss of capital. A practical plan is to invest in smaller installments instead of "
        "deploying all cash on one day, review the portfolio every quarter, "
        "rebalance when one holding becomes too large, and sell when the "
        "business case or your target allocation changes—not simply because "
        "of one short-term price move."
    )
    sections.append(
        "This simulator currently covers the US-listed stocks in its local "
        "watchlist. If you want an India-focused plan, tell me and I can add "
        "an India-specific symbol universe and currency-aware account data. "
        "For a more personal allocation, share your monthly contribution, "
        "time horizon, and low/medium/high risk preference."
    )
    return "\n\n".join(sections)


def format_recommendation_answer(analysis: dict[str, Any]) -> str:
    """Convert recommendation data into a natural-language advisory reply."""
    trader = analysis["trader"]
    cash = analysis["cash"]
    holdings = analysis.get("holdings", {})
    sections: list[str] = []

    if not holdings:
        portfolio_summary = (
            f"{trader} is currently cash-rich with ${cash:.2f} available "
            "and no active positions."
        )
    else:
        largest_symbol = ""
        largest_quantity = -1
        for symbol, shares in holdings.items():
            if shares > largest_quantity:
                largest_symbol = symbol
                largest_quantity = shares
        formatted_holdings = ", ".join(
            f"{format_symbol(symbol)} ({shares} shares)"
            for symbol, shares in holdings.items()
        )
        portfolio_summary = (
            f"{trader} has ${cash:.2f} in cash and currently holds "
            f"{formatted_holdings}. "
            f"Your largest position is {format_symbol(largest_symbol)} "
            f"with {largest_quantity} shares."
        )
    sections.append(portfolio_summary)

    buy_items = analysis.get("buy_recommendations", [])
    sell_items = analysis.get("sell_recommendations", [])
    hold_items = analysis.get("hold_recommendations", [])

    evaluated_symbols = analysis.get("evaluated_symbols", [])
    other_reviewed_symbols = analysis.get("other_reviewed_symbols", [])

    if evaluated_symbols:
        sections.append(
            f"I checked a broader universe of {len(evaluated_symbols)} symbols, "
            "including your current holdings and a wider watchlist, to see "
            "whether any stock deserves a new buy."
        )

    if other_reviewed_symbols:
        formatted_other = ", ".join(
            format_symbol(symbol) for symbol in other_reviewed_symbols[:10]
        )
        sections.append(
            f"Other reviewed stocks outside your current portfolio: {formatted_other}."
        )

    if buy_items:
        top_buy = buy_items[0]
        sections.append(
            f"Best buying opportunity: {format_symbol(top_buy['stock'])} looks strongest right now. "
            f"The trend is {top_buy['trend']}, the current price is "
            f"${top_buy['current_price']:.2f}, and you could buy up to "
            f"{top_buy['max_buy_quantity']} shares with your available cash."
        )

        buy_names = ", ".join(
            format_symbol(item["stock"]) for item in buy_items[:3]
        )
        sections.append(
            f"Suggested buy candidates: {buy_names}. These are the strongest "
            "additions to improve diversification without overconcentrating "
            "in one stock."
        )
    else:
        sections.append(
            "There is no strong buy signal among the stocks I reviewed. The "
            "broader watchlist is not showing a clear buying setup right now, "
            "so the best portfolio improvement is to hold cash and wait for a "
            "healthier entry point."
        )

    if sell_items:
        stock_names = ", ".join(format_symbol(item["stock"]) for item in sell_items[:3])
        sections.append(
            f"Potential profit-taking opportunities: {stock_names}. These are trending upward, so reducing exposure can help lock in gains and protect your portfolio."
        )

    if hold_items:
        watchlist = ", ".join(format_symbol(item["stock"]) for item in hold_items[:3])
        sections.append(
            f"Hold/watchlist names: {watchlist}. They are stable but not strong enough to justify a large new position yet."
        )

    if buy_items:
        lines = ["Recommended buys:"]
        for item in buy_items:
            lines.append(
                f"- {format_symbol(item['stock'])}: {item['trend']} trend, ${item['current_price']:.2f}, max buy quantity {item['max_buy_quantity']}"
            )
        sections.append("\n".join(lines))

    if sell_items:
        lines = ["Recommended sells:"]
        for item in sell_items:
            lines.append(
                f"- {format_symbol(item['stock'])}: {item['trend']} trend, currently holding {item['holding']}, suggested sell-up-to {item['max_sell_quantity']}"
            )
        sections.append("\n".join(lines))

    if not buy_items and hold_items:
        sections.append(
            "If you want to improve diversification later, the calmest names "
            "to review are: "
            + ", ".join(format_symbol(item["stock"]) for item in hold_items[:3])
            + "."
        )

    return "\n\n".join(sections)


async def interactive_portfolio_agent() -> None:
    print("\nAUTONOMOUS TRADING AGENT")
    print("Ask naturally, but include your Trader name '.\n")

    memory = load_conversation_memory()
    current_trader: str | None = memory.get("current_trader")

    while True:
        raw_input = input("You: ").strip()

        if is_exit_command(raw_input):
            print("Goodbye.")
            return

        requested_trader = normalize_trader_name(raw_input)
        if requested_trader:
            current_trader = requested_trader
            memory["current_trader"] = current_trader

        if current_trader is None:
            print(
                "I could not detect a trader in your message. Please say "
                "something like 'I am Trader 1' or 'Trader 2'."
            )
            continue

        save_conversation_memory(memory)

        if is_india_plan_request(raw_input):
            print(
                f"\nAgent: {format_india_plan_answer(current_trader)}\n"
            )
            continue

        preferences = memory.setdefault("traders", {}).setdefault(
            current_trader, {}
        )
        preferences.update(extract_investor_preferences(raw_input))
        memory["traders"][current_trader] = preferences
        save_conversation_memory(memory)

        request = extract_investment_request(raw_input)
        analysis = await analyze_trader_recommendations(
            current_trader,
            request.get("candidate_symbols"),
        )

        if not analysis.get("success"):
            print(f"Unable to analyze trader: {analysis.get('error', 'Unknown error')}")
            continue

        needs_investing_guidance = (
            is_long_term_request(raw_input)
            or bool(preferences)
            or request.get("asks_for_best_stock")
            or request.get("capital") is not None
            or bool(request.get("candidate_symbols"))
            or request.get("concentration_warning")
        )
        if needs_investing_guidance:
            answer = format_long_term_answer(
                analysis,
                preferences,
                request,
            )
        else:
            answer = format_recommendation_answer(analysis)

        print(f"\nAgent: {answer}\n")


if __name__ == "__main__":
    asyncio.run(interactive_portfolio_agent())
