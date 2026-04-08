"""Minimal Yahoo Finance chart API client."""

from __future__ import annotations

import json
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
USER_AGENT = {"User-Agent": "Mozilla/5.0"}


def fetch_chart(symbol: str, range_value: str = "1mo", interval: str = "1d") -> dict:
    encoded_symbol = quote(symbol, safe="")
    url = f"{BASE_URL}/{encoded_symbol}?range={range_value}&interval={interval}"
    request = Request(url, headers=USER_AGENT)

    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    result = payload.get("chart", {}).get("result", [])
    if not result:
        error_payload = payload.get("chart", {}).get("error")
        raise RuntimeError(
            f"Yahoo Finance chart API returned no result for {symbol}. "
            f"Endpoint: {url}. Error: {error_payload or 'empty response'}"
        )

    return result[0]
