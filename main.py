import asyncio
import json
import logging
import traceback

from agents.portfolio_agent import interactive_portfolio_agent
from agents.trader_agent import run_trader
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


# ============================================================
# STOCKS TO ANALYZE
# ============================================================

TRADING_REQUESTS = {
    "Trader 1": "NVDA",
    "Trader 2": "AAPL",
    "Trader 3": "MSFT",
    "Trader 4": "AMZN",
}


# ============================================================
# LOAD TRADERS
# ============================================================

def load_traders():

    with settings.accounts_file.open("r", encoding="utf-8") as file:

        return json.load(file)


# ============================================================
# RUN ALL TRADERS
# ============================================================

async def run_all_traders():

    accounts = load_traders()

    print()
    print("=" * 70)
    print("AUTONOMOUS MCP TRADING SYSTEM")
    print("=" * 70)

    print(
        f"Traders found: {len(accounts)}"
    )

    results = []

    for trader_name in accounts:

        stock = TRADING_REQUESTS.get(
            trader_name
        )

        if not stock:

            print(
                f"\nNo stock configured "
                f"for {trader_name}"
            )

            continue

        print()
        print("-" * 70)
        print(
            f"Running trader: "
            f"{trader_name}"
        )
        print(
            f"Stock requested: "
            f"{stock}"
        )
        print("-" * 70)

        try:

            result = await run_trader(
                trader_name,
                stock
            )

            results.append(
                result
            )

            decision = result[
                "decision"
            ]

            print()
            print(
                f"{trader_name} | "
                f"{stock} | "
                f"{decision['action']} | "
                f"Quantity: "
                f"{decision['quantity']}"
            )

            print(
                f"Price: "
                f"${result['current_price']:.2f}"
            )

            print(
                f"Trend: "
                f"{result['research']['trend']}"
            )

            print(
                f"Validation: "
                f"{decision['validation_status']}"
            )

            print(
                f"Reason: "
                f"{decision['reason']}"
            )

            if result.get(
                "trade_result"
            ):

                print(
                    f"Trade result: "
                    f"{result['trade_result']}"
                )

        except Exception as error:

            print()
            print(
                f"ERROR while running "
                f"{trader_name}:"
            )

            print(
                f"Exception type: "
                f"{type(error).__name__}"
            )

            print(
                f"Exception: {error}"
            )

            traceback.print_exc()

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    for result in results:

        decision = result[
            "decision"
        ]

        print(
            f"{result['trader']} | "
            f"{result['stock']} | "
            f"{decision['action']} | "
            f"Quantity: "
            f"{decision['quantity']} | "
            f"Trend: "
            f"{result['research']['trend']}"
        )

    print()
    print("=" * 70)
    print("RUN COMPLETE")
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        interactive_portfolio_agent()
    )