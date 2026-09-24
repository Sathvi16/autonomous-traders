import unittest

from servers.research_server import calculate_trend


class ResearchTests(unittest.TestCase):
    def test_calculate_trend_rejects_zero_first_price(self):
        result = calculate_trend([{"price": 0}, {"price": 10}])

        self.assertEqual(
            result,
            {
                "success": False,
                "error": "The first valid price cannot be zero",
            },
        )

    def test_calculate_trend_identifies_upward_prices(self):
        result = calculate_trend(
            [{"price": 100}, {"price": 103}, {"price": 105}]
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["trend"], "STRONG_UPWARD")
