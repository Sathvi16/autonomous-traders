from mcp.server.fastmcp import FastMCP
import math

from config import settings

mcp = FastMCP("research-server")


def calculate_trend(prices: list[dict]) -> dict:

    valid_prices = []

    for item in prices:

        raw_price = item.get("price")

        if raw_price is None:
            continue

        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            continue

        if not math.isfinite(price):
            continue

        valid_prices.append(price)

    if len(valid_prices) < 2:
        return {
            "success": False,
            "error": "Not enough valid prices to calculate trend"
        }

    first_price = valid_prices[0]
    last_price = valid_prices[-1]

    if first_price == 0:
        return {
            "success": False,
            "error": "The first valid price cannot be zero"
        }

    total_change = (
        (last_price - first_price) / first_price
    ) * 100

    up_days = 0
    down_days = 0

    for i in range(1, len(valid_prices)):

        if valid_prices[i] > valid_prices[i - 1]:
            up_days += 1

        elif valid_prices[i] < valid_prices[i - 1]:
            down_days += 1

    threshold = settings.trend_threshold_percent

    if total_change >= threshold and up_days > down_days:
        trend = "STRONG_UPWARD"

    elif total_change <= -threshold and down_days > up_days:
        trend = "STRONG_DOWNWARD"

    else:
        trend = "STABLE"

    return {
        "success": True,
        "trend": trend,
        "total_change_percent": round(total_change, 2),
        "up_days": up_days,
        "down_days": down_days,
        "data_points": len(valid_prices)
    }


@mcp.tool()
def research_stock(stock: str, prices: list[dict]) -> dict:

    try:

        result = calculate_trend(prices)

        if not result.get("success"):
            return {
                "success": False,
                "stock": stock,
                "error": result["error"]
            }

        return {
            "success": True,
            "stock": stock,
            "trend": result["trend"],
            "total_change_percent": result["total_change_percent"],
            "up_days": result["up_days"],
            "down_days": result["down_days"],
            "data_points": result["data_points"]
        }

    except Exception as e:

        return {
            "success": False,
            "stock": stock,
            "error": str(e)
        }


if __name__ == "__main__":
    mcp.run()