"""Financial Modeling Prep (FMP) provider.

Wraps the FMP `/stable` REST API: company profile, financial statements
(income/balance/cash flow, annual + quarterly), adjusted daily OHLCV,
peers, analyst estimates, insider trades (Form 4), institutional
holders (13F), and the earnings calendar.

`FMPProvider` is disabled (`available == False`) when no API key is
configured; every public method then returns `None` immediately
without touching the cache or the network. Requests and caching are
delegated to `wbj.providers.base.Provider.get_json` — this module only
builds URLs/params and picks cache keys / max_age_days per data type.

The legacy `/api/v3` routes this module used to call were retired on
2025-08-31 and answer 403 for keys issued after that date. `/stable`
takes the ticker as a `symbol` query parameter rather than in the path.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from wbj.providers.base import Provider

BASE_URL = "https://financialmodelingprep.com/stable"

# max_age_days per cache key, per task brief:
#   ohlcv_daily/quote 1, analyst_estimates 7, statements 30,
#   profile/peers/holders/insiders 7.
_MAX_AGE_OHLCV = 1
_MAX_AGE_ESTIMATES = 7
_MAX_AGE_STATEMENT = 30
_MAX_AGE_REFERENCE = 7


def _years_ago(d: date, years: int) -> date:
    """Return the date `years` years before `d`, handling Feb 29 safely."""
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        # d is Feb 29 and target year isn't a leap year.
        return d.replace(month=2, day=28, year=d.year - years)


def _adjusted_bar(row: dict[str, Any]) -> dict[str, Any]:
    """Map one `/stable` dividend-adjusted bar onto the OHLCV bar shape.

    `/stable/historical-price-eod/dividend-adjusted` names every field
    `adj*`; the packet expects `open`/`high`/`low`/`close` already
    adjusted, plus `adjClose`. The whole series is adjusted, so `close`
    and `adjClose` carry the same value.
    """
    adj_close = row.get("adjClose")
    return {
        "date": row.get("date"),
        "open": row.get("adjOpen"),
        "high": row.get("adjHigh"),
        "low": row.get("adjLow"),
        "close": adj_close,
        "adjClose": adj_close,
        "volume": row.get("volume"),
    }


class FMPProvider(Provider):
    """Financial Modeling Prep data provider."""

    @property
    def available(self) -> bool:
        """True iff an FMP API key is configured."""
        return bool(self.settings and getattr(self.settings, "fmp_api_key", None))

    def _params(self, **extra: Any) -> dict[str, Any]:
        params = {"apikey": self.settings.fmp_api_key}
        params.update(extra)
        return params

    def profile(self, t: str) -> list | dict | None:
        """Company profile: name, sector, industry, market cap, etc."""
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/profile",
            self._params(symbol=t),
            "profile",
            t,
            max_age_days=_MAX_AGE_REFERENCE,
        )

    def income_annual(self, t: str, limit: int = 6) -> list | dict | None:
        """Annual income statements, most recent `limit` fiscal years."""
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/income-statement",
            self._params(symbol=t, period="annual", limit=limit),
            "income_annual",
            t,
            max_age_days=_MAX_AGE_STATEMENT,
        )

    def income_quarterly(self, t: str, limit: int = 21) -> list | dict | None:
        """Quarterly income statements, most recent `limit` quarters."""
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/income-statement",
            self._params(symbol=t, period="quarter", limit=limit),
            "income_quarterly",
            t,
            max_age_days=_MAX_AGE_STATEMENT,
        )

    def balance_annual(self, t: str, limit: int = 6) -> list | dict | None:
        """Annual balance sheet statements, most recent `limit` fiscal years."""
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/balance-sheet-statement",
            self._params(symbol=t, period="annual", limit=limit),
            "balance_annual",
            t,
            max_age_days=_MAX_AGE_STATEMENT,
        )

    def balance_quarterly(self, t: str, limit: int = 21) -> list | dict | None:
        """Quarterly balance sheet statements, most recent `limit` quarters."""
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/balance-sheet-statement",
            self._params(symbol=t, period="quarter", limit=limit),
            "balance_quarterly",
            t,
            max_age_days=_MAX_AGE_STATEMENT,
        )

    def cashflow_annual(self, t: str, limit: int = 6) -> list | dict | None:
        """Annual cash flow statements, most recent `limit` fiscal years."""
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/cash-flow-statement",
            self._params(symbol=t, period="annual", limit=limit),
            "cashflow_annual",
            t,
            max_age_days=_MAX_AGE_STATEMENT,
        )

    def cashflow_quarterly(self, t: str, limit: int = 21) -> list | dict | None:
        """Quarterly cash flow statements, most recent `limit` quarters."""
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/cash-flow-statement",
            self._params(symbol=t, period="quarter", limit=limit),
            "cashflow_quarterly",
            t,
            max_age_days=_MAX_AGE_STATEMENT,
        )

    def ohlcv_daily(
        self, t: str, years: int = 3, today: date | None = None
    ) -> list | None:
        """Split/dividend-adjusted daily OHLCV for the past `years` years.

        `today` anchors the `from`/`to` window and must be supplied by the
        caller (e.g. the CLI passes `date.today()`) so this stays
        deterministic under test. Returns a list of adjusted bars, or None
        if unavailable/missing.
        """
        if not self.available:
            return None
        if today is None:
            today = date.today()
        from_date = _years_ago(today, years)
        payload = self.get_json(
            f"{BASE_URL}/historical-price-eod/dividend-adjusted",
            self._params(
                symbol=t, **{"from": from_date.isoformat(), "to": today.isoformat()}
            ),
            "ohlcv_daily",
            t,
            max_age_days=_MAX_AGE_OHLCV,
        )
        if not isinstance(payload, list):
            return None
        return [_adjusted_bar(row) for row in payload]

    def peers(self, t: str) -> list | dict | None:
        """Peer tickers for `t`."""
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/stock-peers",
            self._params(symbol=t),
            "peers",
            t,
            max_age_days=_MAX_AGE_REFERENCE,
        )

    def analyst_estimates(
        self, t: str, period: str = "annual", limit: int = 10
    ) -> list | dict | None:
        """Analyst revenue/EPS estimates.

        `/stable` rejects the request with 400 unless `period` is given.
        """
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/analyst-estimates",
            self._params(symbol=t, period=period, limit=limit),
            "analyst_estimates",
            t,
            max_age_days=_MAX_AGE_ESTIMATES,
        )

    def insider_trades(self, t: str) -> list | dict | None:
        """SEC Form 4 insider trades, most recent 200.

        Restricted on entry-level FMP plans (402); `get_json` then returns
        None. SEC EDGAR and FinnHub cover the same Form 4 data for free.
        """
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/insider-trading/search",
            self._params(symbol=t, limit=200),
            "insider_trades",
            t,
            max_age_days=_MAX_AGE_REFERENCE,
        )

    def institutional_holders(
        self, t: str, year: int | None = None, quarter: int | None = None
    ) -> list | dict | None:
        """13F institutional holders for a given filing quarter.

        Defaults to the most recently completed calendar quarter. Restricted
        on entry-level FMP plans (402), so this path is unverified against a
        live response; SEC EDGAR carries the same 13F filings for free.
        """
        if not self.available:
            return None
        if year is None or quarter is None:
            today = date.today()
            prev_quarter = (today.month - 1) // 3  # 0 when today is in Q1
            year = today.year if prev_quarter else today.year - 1
            quarter = prev_quarter or 4
        return self.get_json(
            f"{BASE_URL}/institutional-ownership/symbol-positions-summary",
            self._params(symbol=t, year=year, quarter=quarter),
            "institutional_holders",
            t,
            max_age_days=_MAX_AGE_REFERENCE,
        )

    def earnings_calendar(self, t: str, limit: int = 40) -> list | dict | None:
        """Historical earnings calendar (actual vs. estimated EPS/revenue)."""
        if not self.available:
            return None
        return self.get_json(
            f"{BASE_URL}/earnings",
            self._params(symbol=t, limit=limit),
            "earnings_calendar",
            t,
            max_age_days=_MAX_AGE_REFERENCE,
        )
