"""Live EU ETS Carbon Price Service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from backend.services.real_data_service import real_data_service
from backend.services.yahoo_finance_client import fetch_chart


ETS_SYMBOL = "CFI2=F"


@dataclass
class ETSPriceData:
    current_price_eur: float
    price_date: str
    change_24h: float
    change_pct_24h: float
    high_52w: float
    low_52w: float
    average_30d: float
    source: str
    instrument: str
    is_live: bool
    last_updated: str


def _history_to_rows(history_frame) -> List[Dict]:
    timestamps = history_frame.get("timestamp", [])
    closes = history_frame.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    history = []

    for timestamp, close_value in zip(timestamps, closes):
        if close_value is None:
            continue
        history.append(
            {
                "date": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d"),
                "price": round(float(close_value), 2),
            }
        )
    return history


def _fetch_price_history_sync(period: str):
    history = fetch_chart(ETS_SYMBOL, range_value=period)
    rows = _history_to_rows(history)
    if not rows:
        raise RuntimeError(f"Yahoo Finance returned no close prices for {ETS_SYMBOL}.")
    return history, rows


def _fetch_market_price_sync() -> ETSPriceData:
    history, rows = _fetch_price_history_sync("1y")
    meta = history.get("meta", {})
    quote = history.get("indicators", {}).get("quote", [{}])[0]

    closes = [row["price"] for row in rows]
    highs = [float(value) for value in quote.get("high", []) if value is not None]
    lows = [float(value) for value in quote.get("low", []) if value is not None]

    current_price = round(float(meta.get("regularMarketPrice", closes[-1])), 2)
    previous_close = round(float(closes[-2] if len(closes) > 1 else closes[-1]), 2)
    change_24h = round(current_price - previous_close, 2)
    change_pct = round((change_24h / previous_close) * 100, 2) if previous_close else 0.0
    high_52w = round(float(meta.get("fiftyTwoWeekHigh", max(highs) if highs else current_price)), 2)
    low_52w = round(float(meta.get("fiftyTwoWeekLow", min(lows) if lows else current_price)), 2)
    trailing_month = closes[-30:] if len(closes) >= 30 else closes
    average_30d = round(sum(trailing_month) / len(trailing_month), 2)
    price_date = rows[-1]["date"]
    now = datetime.now()

    return ETSPriceData(
        current_price_eur=current_price,
        price_date=price_date,
        change_24h=change_24h,
        change_pct_24h=change_pct,
        high_52w=high_52w,
        low_52w=low_52w,
        average_30d=average_30d,
        source="Yahoo Finance chart API (ICE EUA Futures CFI2=F)",
        instrument=ETS_SYMBOL,
        is_live=True,
        last_updated=now.isoformat(),
    )


class ETSPriceService:
    def __init__(self) -> None:
        self.cached_price: Optional[ETSPriceData] = None
        self.last_fetch: Optional[datetime] = None

    async def get_current_price(self) -> ETSPriceData:
        """
        Get current ETS price. Uses a 1-hour cache and performs blocking I/O in
        a worker thread.
        """
        if self.last_fetch and self.cached_price:
            if (datetime.now() - self.last_fetch).total_seconds() < 3600:
                return self.cached_price

        try:
            price_data = await asyncio.to_thread(_fetch_market_price_sync)
            self.cached_price = price_data
            self.last_fetch = datetime.now()
        except Exception as exc:  # noqa: BLE001
            print(f"ETS live fetch failed: {exc}")
            if self.cached_price is None:
                fallback = await asyncio.to_thread(real_data_service.get_real_carbon_price_sync)
                self.cached_price = ETSPriceData(
                    current_price_eur=fallback.price_eur,
                    price_date=datetime.now().strftime("%Y-%m-%d"),
                    change_24h=0.0,
                    change_pct_24h=0.0,
                    high_52w=fallback.price_eur,
                    low_52w=fallback.price_eur,
                    average_30d=fallback.price_eur,
                    source=fallback.source,
                    instrument="CFI2=F",
                    is_live=fallback.is_live,
                    last_updated=fallback.timestamp,
                )
                self.last_fetch = datetime.now()

        return self.cached_price

    def get_price_history(self, days: int = 30) -> List[Dict]:
        try:
            bounded_days = max(1, min(days, 365))
            _, rows = _fetch_price_history_sync(f"{bounded_days}d")
            return rows[-bounded_days:]
        except Exception as exc:  # noqa: BLE001
            print(f"ETS history fetch failed: {exc}")
            return []

    def get_price_forecast(self, months: int = 6) -> List[Dict]:
        del months
        return []


ets_service = ETSPriceService()


def get_ets_price() -> float:
    """
    Non-blocking accessor for synchronous callers. Returns the cached price only
    and never triggers a network call.
    """
    if not ets_service.cached_price:
        return 0.0
    return ets_service.cached_price.current_price_eur
