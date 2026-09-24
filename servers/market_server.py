from mcp.server.fastmcp import FastMCP
import math
import sys
from contextlib import redirect_stdout

mcp = FastMCP("market-server")


def load_yfinance():
    import yfinance as yf
    return yf


@mcp.tool()
def get_price(stock: str) -> dict:
    """
    Get the latest available market price for a stock.
    """

    try:
        yf = load_yfinance()

        ticker = yf.Ticker(stock)

        # Redirect any library output away from MCP stdout.
        with redirect_stdout(sys.stderr):
            history = ticker.history(
                period="5d",
                interval="1d",
                auto_adjust=False,
                actions=False
            )

        if history.empty:
            return {
                "success": False,
                "error": f"No market data found for {stock}"
            }

        # Get Close prices and remove invalid values.
        close_prices = history["Close"].dropna()

        if close_prices.empty:
            return {
                "success": False,
                "error": f"No valid price found for {stock}"
            }

        latest_price = float(close_prices.iloc[-1])

        if not math.isfinite(latest_price):
            return {
                "success": False,
                "error": f"Invalid price returned for {stock}"
            }

        return {
            "success": True,
            "stock": stock,
            "price": latest_price
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def get_market_history(stock: str, days: int = 5) -> dict:
    """
    Get recent valid closing prices for a stock.
    """

    try:
        if days <= 0:
            return {
                "success": False,
                "error": "Days must be greater than zero.",
            }

        yf = load_yfinance()

        ticker = yf.Ticker(stock)

        with redirect_stdout(sys.stderr):
            history = ticker.history(
                period="10d",
                interval="1d",
                auto_adjust=False,
                actions=False
            )

        if history.empty:
            return {
                "success": False,
                "error": f"No market history found for {stock}"
            }

        prices = []

        for index, row in history.iterrows():

            raw_price = row.get("Close")

            # Ignore None / NaN / invalid values.
            if raw_price is None:
                continue

            try:
                price = float(raw_price)
            except (TypeError, ValueError):
                continue

            if not math.isfinite(price):
                continue

            prices.append({
                "date": index.strftime("%Y-%m-%d"),
                "price": price
            })

        # Keep only the requested number of valid records.
        prices = prices[-days:]

        if not prices:
            return {
                "success": False,
                "error": f"No valid closing prices found for {stock}"
            }

        return {
            "success": True,
            "stock": stock,
            "prices": prices
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def get_price_change(stock: str) -> dict:
    """
    Calculate price change using the latest two valid prices.
    """

    try:
        result = get_market_history(stock, 2)

        if not result.get("success"):
            return result

        prices = result["prices"]

        if len(prices) < 2:
            return {
                "success": False,
                "error": f"Not enough valid price data for {stock}"
            }

        previous_price = float(prices[-2]["price"])
        current_price = float(prices[-1]["price"])

        change = current_price - previous_price

        if previous_price == 0:
            percentage = 0
        else:
            percentage = (change / previous_price) * 100

        return {
            "success": True,
            "stock": stock,
            "previous_price": previous_price,
            "current_price": current_price,
            "change": change,
            "percentage": percentage
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    mcp.run()