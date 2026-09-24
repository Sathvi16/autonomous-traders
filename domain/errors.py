"""Expected domain errors."""


class TradingError(Exception):
    """Base class for expected trading failures."""


class TraderNotFoundError(TradingError):
    """The requested trader does not exist."""


class InvalidAccountError(TradingError):
    """Persisted account data is invalid."""


class InvalidTradeError(TradingError):
    """A trade request does not satisfy basic validation."""


class InsufficientCashError(TradingError):
    """The account cannot afford a purchase."""


class InsufficientSharesError(TradingError):
    """The account does not own enough shares to sell."""
