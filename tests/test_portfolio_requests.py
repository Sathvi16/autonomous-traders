import unittest

from agents.portfolio_agent import (
    extract_investment_request,
    extract_investor_preferences,
    format_long_term_answer,
    format_india_plan_answer,
    is_india_plan_request,
)


class PortfolioRequestTests(unittest.TestCase):
    def test_extracts_rupee_lakh_budget(self):
        request = extract_investment_request("I have ₹1 lakh capital")
        self.assertEqual(request["capital"], 100000)
        self.assertEqual(request["currency"], "INR")

    def test_small_budget_is_detected(self):
        request = extract_investment_request("I have 5000 capital")
        self.assertEqual(request["capital"], 5000)

    def test_detects_duplicate_and_invalid_tickers(self):
        request = extract_investment_request("Review AAPL AAPL AAPL and ZZZZ")
        self.assertEqual(request["duplicate_symbols"], ["AAPL"])
        self.assertEqual(request["invalid_symbols"], ["ZZZZ"])

    def test_detects_concentration_risk(self):
        request = extract_investment_request("Invest 100% in AAPL")
        self.assertTrue(request["concentration_warning"])

    def test_best_stock_without_profile_is_explicit(self):
        request = extract_investment_request("What is the best stock?")
        answer = format_long_term_answer(
            {
                "trader": "Trader 1",
                "cash": 1000,
                "holdings": {},
                "all_recommendations": [],
            },
            {},
            request,
        )
        self.assertIn("time horizon and risk tolerance", answer)

    def test_long_term_answer_documents_selection_criteria(self):
        preferences = extract_investor_preferences(
            "I want to invest for 10 years with low risk"
        )
        request = extract_investment_request(
            "Review AAPL MSFT GOOGL AMZN JPM V UNH COST"
        )
        answer = format_long_term_answer(
            {
                "trader": "Trader 1",
                "cash": 100000,
                "holdings": {},
                "all_recommendations": [],
            },
            preferences,
            request,
        )
        self.assertIn("business quality, financial strength, valuation", answer)
        self.assertIn("sector diversification", answer)

    def test_detects_india_plan_request(self):
        self.assertTrue(is_india_plan_request("india-focused-plan"))
        self.assertTrue(is_india_plan_request("Suggest an Indian portfolio"))
        self.assertFalse(is_india_plan_request("Which US stocks should I buy?"))

    def test_india_plan_does_not_mix_us_account_currency(self):
        answer = format_india_plan_answer("Trader 2")
        self.assertIn("HDFC Bank (HDFCBANK.NS)", answer)
        self.assertIn("US-dollar cash", answer)
        self.assertNotIn("Illustrative allocation for the available cash", answer)


if __name__ == "__main__":
    unittest.main()
