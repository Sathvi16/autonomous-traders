import json
from pathlib import Path
import tempfile
import unittest

from domain.errors import InsufficientCashError, InsufficientSharesError
from domain.models import TradeAction, TradeRequest
from repositories.account_repository import JsonAccountRepository
from services.account_service import AccountService


class AccountServiceTests(unittest.TestCase):
    def make_service(self):
        self.tmp_path = tempfile.TemporaryDirectory()
        path = Path(self.tmp_path.name) / "accounts.json"
        path.write_text(
            json.dumps(
                {
                    "Trader 1": {
                        "cash": 100,
                        "holdings": {"AAPL": 2},
                    }
                }
            ),
            encoding="utf-8",
        )
        return AccountService(JsonAccountRepository(path)), path

    def tearDown(self):
        self.tmp_path.cleanup()

    def test_buy_updates_cash_and_holdings(self):
        service, path = self.make_service()

        result = service.execute_trade(
            TradeRequest("Trader 1", TradeAction.BUY, "AAPL", 10, 3)
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["shares"], 5)
        self.assertEqual(result["cash"], 70)
        self.assertEqual(json.loads(path.read_text())["Trader 1"]["cash"], 70)


    def test_sell_rejects_more_than_owned(self):
        service, _ = self.make_service()

        with self.assertRaises(InsufficientSharesError):
            service.execute_trade(
                TradeRequest("Trader 1", TradeAction.SELL, "AAPL", 10, 3)
            )
    def test_buy_rejects_insufficient_cash(self):
        service, _ = self.make_service()

        with self.assertRaises(InsufficientCashError):
            service.execute_trade(
                TradeRequest("Trader 1", TradeAction.BUY, "AAPL", 101, 1)
            )
