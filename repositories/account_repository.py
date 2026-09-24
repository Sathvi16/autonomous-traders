"""JSON-backed account persistence."""

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from domain.errors import InvalidAccountError, TraderNotFoundError
from domain.models import Account


class JsonAccountRepository:
    """Loads and saves accounts without exposing JSON details to services."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load_all(self) -> dict[str, Account]:
        try:
            with self.path.open("r", encoding="utf-8") as file:
                raw_accounts = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise InvalidAccountError(
                f"Unable to load accounts from {self.path}: {error}"
            ) from error

        if not isinstance(raw_accounts, dict):
            raise InvalidAccountError("Accounts file must contain an object.")

        return {
            str(name): self._parse_account(name, value)
            for name, value in raw_accounts.items()
        }

    def get(self, trader_name: str) -> Account:
        accounts = self.load_all()
        try:
            return accounts[trader_name]
        except KeyError as error:
            raise TraderNotFoundError(
                f"Trader '{trader_name}' was not found."
            ) from error

    def save_all(self, accounts: dict[str, Account]) -> None:
        payload = {
            name: account.to_dict()
            for name, account in accounts.items()
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                delete=False,
            ) as file:
                json.dump(payload, file, indent=4)
                file.write("\n")
                temporary_path = Path(file.name)
            os.replace(temporary_path, self.path)
        except OSError as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise InvalidAccountError(
                f"Unable to save accounts to {self.path}: {error}"
            ) from error

    @staticmethod
    def _parse_account(name: str, raw: Any) -> Account:
        if not isinstance(raw, dict):
            raise InvalidAccountError(f"Invalid account for '{name}'.")
        try:
            cash = float(raw.get("cash", 0))
            raw_holdings = raw.get("holdings", {})
            if not isinstance(raw_holdings, dict):
                raise TypeError("holdings must be an object")
            holdings = {
                str(stock).upper().strip(): int(shares)
                for stock, shares in raw_holdings.items()
            }
        except (TypeError, ValueError) as error:
            raise InvalidAccountError(
                f"Invalid account data for '{name}': {error}"
            ) from error

        if cash < 0 or any(shares < 0 for shares in holdings.values()):
            raise InvalidAccountError(
                f"Account '{name}' cannot contain negative balances."
            )
        return Account(cash=cash, holdings=holdings)
