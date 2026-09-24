import unittest

from agents.trader_agent import apply_trend_strategy


class TraderStrategyTests(unittest.TestCase):
    def test_upward_trend_forces_sell(self):
        result = apply_trend_strategy(
            {
                "success": True,
                "action": "BUY",
                "quantity": 2,
                "reason": "Model reason",
            },
            {"trend": "STRONG_UPWARD"},
        )

        self.assertEqual(result["action"], "SELL")
        self.assertEqual(result["quantity"], 2)

    def test_downward_trend_forces_buy(self):
        result = apply_trend_strategy(
            {
                "success": True,
                "action": "SELL",
                "quantity": 1,
                "reason": "Model reason",
            },
            {"trend": "STRONG_DOWNWARD"},
        )

        self.assertEqual(result["action"], "BUY")

    def test_stable_trend_holds(self):
        result = apply_trend_strategy(
            {
                "success": True,
                "action": "BUY",
                "quantity": 1,
                "reason": "Model reason",
            },
            {"trend": "STABLE"},
        )

        self.assertEqual(result["action"], "HOLD")
        self.assertEqual(result["quantity"], 0)
